# Django Query Inspector Plus (QuIP)

Query Inspector Plus (QuIP) is a Django application providing middleware for
inspecting and reporting SQL queries executed for each web request. Duplicate
queries can easily be identified using this tool, with full support for
asynchronous requests (e.g. AJAX).

Works with Django (1.11 and later) and Python (2.7, 3.4 and later).

Example log output:

    [SQL] 17 queries (4 duplicates), 34 ms SQL time, 243 ms total request time

Statistics can also be added to the response headers, for easier debugging
without having to manually look through server logs:

    X-QueryInspect-Num-SQL-Queries: 17
    X-QueryInspect-Duplicate-SQL-Queries: 4
    X-QueryInspect-Total-SQL-Time: 34 ms
    X-QueryInspect-Total-Request-Time: 243 ms

Duplicate queries can also be shown in the log:

    [SQL] repeated query (6x): SELECT "customer_role"."id",
        "customer_role"."contact_id", "customer_role"."name"
        FROM "customer_role" WHERE "customer_role"."contact_id" = ?

The duplicate queries are detected by ignoring any integer values in the SQL
statement. The reasoning is that most of the duplicate queries in Django are
due to results not being cached or pre-fetched properly, so Django needs to
look up related fields afterwards. This lookup is done by the object ID, which
is in most cases an integer.

The heuristic is not 100% precise so it may have some false positives or
negatives, but is a very good starting point for most Django projects.

For each duplicate query, the Python traceback can also be shown, which may
help with identifying why the query has been executed:

    File "/vagrant/api/views.py", line 178, in get
        return self.serialize(self.object_qs)
    File "/vagrant/customer/views.py", line 131, in serialize
        return serialize(objs, include=includes)
    File "/vagrant/customer/serializers.py", line 258, in serialize_contact
        lambda obj: [r.name for r in obj.roles.all()]),
    File "/vagrant/customer/serializers.py", line 258, in <lambda>
        lambda obj: [r.name for r in obj.roles.all()]),

## Quick Start

Install from the Python Package Index:

    pip install django-queryinspect

Add the middleware to your Django settings:

    MIDDLEWARE_CLASSES += (
        'qinspect.middleware.QueryInspectMiddleware',
    )

Enable Django's `DEBUG` setting (the SQL query logging doesn't work without
it):

    DEBUG = True

Update your logging configuration so the output from the queryinspect app
shows up:

    LOGGING = {
        ...
        'handlers': {
            ...
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
            ...
        },

        'loggers': {
            ...
            'qinspect': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
        ...
    }

By default, Query Inspector will log stats for each request via the Django
logging mechanism and via HTTP headers in the response. This default
behavior can be modified by specifying several settings values in your
Django settings file (see next section)

## Configuration

Query Inspector can be configured a number of ways through a configuration
dictionary. Simply set up a corresponding dict in your **settings.py** file,
overriding the necessary values.

    # NOTE: All values shown are the default values
    QUERY_INSPECT_CONFIG = {
        # Whether Query Inspector should do anything
        'enabled': False,

        # Absolute limit (in milliseconds) above which queries should be logged.
        # A value of None disables this feature.
        'absolute_limit': None,

        # Add stats to response headers
        'header_stats': True,

        # Log all query SQL commands
        'log_all_queries': False,

        # Log stats on duplicate queries
        'log_duplicates': False,

        # Log general query stats
        'log_stats': True,

        # Include tracebacks in log output
        'log_tracebacks': False,

        # Specifies the number of duplicate queries for which traceback output
        # should be printed. Increasing this value can be useful for tracking
        # down where duplicate query calls are occurring in your code.
        'log_tracebacks_duplicate_limit': 1,

        # Number of standard deviations above the mean query time for which
        # queries should be logged. A value of None disables this feature.
        'standard_deviation_limit': None,

        # List of directories to filter against when printing tracebacks. See
        # documentation below for more.
        'traceback_roots': [],

        # List of directories to exclude when printing tracebacks. See
        # documentation below for more.
        'traceback_roots_exclude': [],
    }

## Traceback roots

Complete tracebacks of an entire request are usually huge, but only a few
entries in the traceback are of the interest (usually only the few that
represent the code you're working on). To include only those entries of
interest in the traceback, you can set `traceback_roots` in the
`QUERY_INSPECT_CONFIG` dictionary to a list of paths.  If the path for a code
file in the traceback begins with any of the paths in this list, it will be
included in the traceback.

The `traceback_roots_exclude` option is also available, allowing you to filter
out sub-folders from entries that appear in the `traceback_roots` option. This
is particularly helpful in cases where a virtual environment may exist within
the working directory.

Here's an example of how both can be used together:

    import os

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    # Example of traceback_roots filtering
    QUERY_INSPECT_CONFIG = {
        # ...
        'traceback_roots': [BASE_DIR],
        'traceback_roots_exclude': [os.path.join(BASE_DIR, 'venv')],
        # ...
    }

## Testing

To run tests just use `tox` command (https://pypi.python.org/pypi/tox)

    tox  # for all supported python and django versions

If you need you can run tox just for single environment, for instance:

    tox -e py36-django111

For available test environments refer to `tox.ini` file.


## License

Copyright (C) 2014-2019. Good Code and Django Query Inspector contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
