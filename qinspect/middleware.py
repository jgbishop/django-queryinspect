import logging
import collections
import re
import time
import traceback
import math

from django.conf import settings
from django.db import connection
from django.core.exceptions import MiddlewareNotUsed
try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    class MiddlewareMixin(object):
        def __init__(self, get_response=None):
            pass


try:
    from django.db.backends.utils import CursorDebugWrapper
except ImportError:
    from django.db.backends.util import CursorDebugWrapper

if hasattr(logging, 'NullHandler'):
    NullHandler = logging.NullHandler
else:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

# Set up the default configuration
cfg = {
    'enabled': False,

    'absolute_limit': None,
    'header_stats': True,
    'log_queries': False,
    'log_stats': True,
    'log_tracebacks': False,
    'standard_deviation_limit': None,
    'traceback_roots': [],
}

# Pull in the user's configuration and update accordingly
user_cfg = getattr(settings, "QUERY_INSPECT_CONFIG", {})
cfg.update(user_cfg)
cfg['enabled'] = bool(settings.DEBUG and cfg['enabled'])

__all__ = ['QueryInspectMiddleware']


class QueryInspectMiddleware(MiddlewareMixin):

    class QueryInfo(object):
        __slots__ = ('sql', 'time', 'tb')

    sql_id_pattern = re.compile(r'=\s*\d+')

    @classmethod
    def patch_cursor(cls):
        real_exec = CursorDebugWrapper.execute
        real_exec_many = CursorDebugWrapper.executemany

        def should_include(path):
            if path == __file__ or path + 'c' == __file__:
                return False

            roots = cfg.get("traceback_roots")
            if not roots:
                return True
            else:
                for root in roots:
                    if path.startswith(root):
                        return True
                return False

        def tb_wrap(fn):
            def wrapper(self, *args, **kwargs):
                try:
                    return fn(self, *args, **kwargs)
                finally:
                    if hasattr(self.db, 'queries'):
                        tb = traceback.extract_stack()
                        tb = [f for f in tb if should_include(f[0])]
                        self.db.queries[-1]['tb'] = tb

            return wrapper

        CursorDebugWrapper.execute = tb_wrap(real_exec)
        CursorDebugWrapper.executemany = tb_wrap(real_exec_many)

    @classmethod
    def get_query_details(cls, queries):
        retval = []
        for q in queries:
            if q['sql'] is None:
                continue

            qi = cls.QueryInfo()
            qi.sql = cls.sql_id_pattern.sub('= ?', q['sql'])
            qi.time = float(q['time'])
            qi.tb = q.get('tb')
            retval.append(qi)
        return retval

    @staticmethod
    def count_duplicates(details):
        buf = collections.defaultdict(lambda: 0)
        for qi in details:
            buf[qi.sql] = buf[qi.sql] + 1
        return sorted(buf.items(), key=lambda el: el[1], reverse=True)

    @staticmethod
    def group_queries(details):
        buf = collections.defaultdict(lambda: [])
        for qi in details:
            buf[qi.sql].append(qi)
        return buf

    @classmethod
    def check_duplicates(cls, details):
        duplicates = [
            (qi, num) for qi, num in cls.count_duplicates(details) if num > 1
        ]
        n = 0
        if len(duplicates) > 0:
            n = (sum(num for qi, num in duplicates) - len(duplicates))

        dup_groups = cls.group_queries(details)

        if cfg['log_queries']:
            for sql, num in duplicates:
                log.warning('[SQL] repeated query (%dx): %s' % (num, sql))
                if cfg['log_tracebacks'] and dup_groups[sql]:
                    log.warning(
                        'Traceback:\n' +
                        ''.join(traceback.format_list(dup_groups[sql][0].tb)))

        return n

    @classmethod
    def check_stddev_limit(cls, details):
        total = sum(qi.time for qi in details)
        n = len(details)

        if cfg['stddev_limit'] is None or n == 0:
            return

        mean = total / n
        stddev_sum = sum(math.sqrt((qi.time - mean) ** 2) for qi in details)
        if n < 2:
            stddev = 0
        else:
            stddev = math.sqrt((1.0 / (n - 1)) * (stddev_sum / n))

        query_limit = mean + (stddev * cfg['stddev_limit'])

        for qi in details:
            if qi.time > query_limit:
                log.warning(
                    '[SQL] query execution of %d ms over limit of '
                    '%d ms (%d dev above mean): %s' % (
                        qi.time * 1000,
                        query_limit * 1000,
                        cfg['stddev_limit'],
                        qi.sql))

    @classmethod
    def check_absolute_limit(cls, details):
        n = len(details)
        if cfg['absolute_limit'] is None or n == 0:
            return

        query_limit = cfg['absolute_limit'] / 1000.0

        for qi in details:
            if qi.time > query_limit:
                log.warning(
                    '[SQL] query execution of %d ms over absolute '
                    'limit of %d ms: %s' % (
                        qi.time * 1000,
                        query_limit * 1000,
                        qi.sql))

    @classmethod
    def output_stats(cls, details, num_duplicates, request_time, response):
        sql_time = sum(qi.time for qi in details)
        n = len(details)

        if cfg['log_stats']:
            log.info(
                '[SQL] %d queries (%d duplicates), %d ms SQL time, '
                '%d ms total request time' % (
                    n,
                    num_duplicates,
                    sql_time * 1000,
                    request_time * 1000))

        if cfg['header_stats']:
            response['X-QueryInspect-Num-SQL-Queries'] = str(n)
            response['X-QueryInspect-Total-SQL-Time'] = '%d ms' % (
                sql_time * 1000)
            response['X-QueryInspect-Total-Request-Time'] = '%d ms' % (
                request_time * 1000)
            response['X-QueryInspect-Duplicate-SQL-Queries'] = str(
                num_duplicates)

    def __init__(self, get_response=None):
        if not cfg['enabled']:
            raise MiddlewareNotUsed()
        super(QueryInspectMiddleware, self).__init__(get_response)

    def process_request(self, request):
        self.request_start = time.time()
        self.conn_queries_len = len(connection.queries)

    def process_response(self, request, response):
        if not hasattr(self, "request_start"):
            return response

        request_time = time.time() - self.request_start

        details = self.get_query_details(
            connection.queries[self.conn_queries_len:])

        num_duplicates = self.check_duplicates(details)
        self.check_stddev_limit(details)
        self.check_absolute_limit(details)
        self.output_stats(details, num_duplicates, request_time, response)

        return response


if cfg['enabled'] and cfg['log_tracebacks']:
    QueryInspectMiddleware.patch_cursor()
