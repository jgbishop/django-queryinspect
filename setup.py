#!/usr/bin/env python

import os
import sys
from setuptools import setup, find_packages, Command


class BaseCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


class TestCommand(BaseCommand):

    description = "run self-tests"

    def run(self):
        os.chdir('testproject')
        ret = os.system('%s manage.py test testapp' % sys.executable)
        if ret != 0:
            sys.exit(-1)

setup(
    name='django-quip',
    version='1.0.0',
    description='Django Query Inspector Plus - SQL query inspector for Django',
    author='Senko Rasic, Jonah Bishop',
    author_email='jb@borngeek.com',
    url='https://github.com/jgbishop/django-quip',
    license='MIT',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(),
    install_requires=['Django>=1.11'],
    cmdclass={
        'test': TestCommand,
    }
)
