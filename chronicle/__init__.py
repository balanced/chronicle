from __future__ import unicode_literals

import argparse
import importlib
import re
import logging


__version__ = '1.0.7'


class LogLevelAction(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        level = getattr(logging, values.upper())
        setattr(namespace, self.dest, level)


class LogNoiseFilter(logging.Filter):

    excludes = [
        (
            logging.WARNING,
            'newrelic.core.data_collector',
            re.compile('^Data collector is (not contactable|unavailable)\..*')
        ),
        (
            logging.WARNING,
            'newrelic.core.data_collector',
            re.compile('^An unexpected HTTP response was received.*')
        ),
        (
            logging.ERROR,
            'newrelic.core.application',
            re.compile('^Unable to report main transaction metrics.*')
        ),
        (
            logging.ERROR,
            'celery.worker.consumer',
            re.compile('^consumer: Connection to broker lost.*')
        ),
        (
            logging.ERROR,
            'newrelic.core.application',
            re.compile('^Registration of the application.*'),
        ),
        (
            logging.WARN,
            'kombu.mixins',
            re.compile('^Connection to broker lost.*')
        )
    ]

    def filter(self, record):
        for levelno, name, msg_pattern in self.excludes:
            if (record.levelno == levelno and
                        record.name == name and
                        msg_pattern.match(record.message) is not None):
                return False
        return True


def add_logging_opts(parser):
    choices = [
        'DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL'
    ]
    parser.add_argument(
        '-l', '--log-level',
        default=logging.WARNING,
        help='Set the logging level',
        choices=[c for c in choices] + [c.lower() for c in choices],
        action=LogLevelAction,
    )
    parser.add_argument(
        '--enable-syslog', action='store_true', default=False)
    parser.add_argument(
        '--disable-stderrlog', action='store_true', default=False)
    parser.add_argument(
        '--enable-emaillog', action='store_true', default=False)
    parser.add_argument(
        '--enable-sentrylog', action='store_true', default=False)


class BalancedParser(argparse.ArgumentParser):

    def __init__(self, *a, **kw):
        super(BalancedParser, self).__init__(*a, **kw)
        add_logging_opts(self)

    def configure_logging(self, logging_fn, args=None):
        args = args or self.parse_args()
        logging_fn(
            enable_console=not args.disable_stderrlog,
            enable_syslog=args.enable_syslog,
            enable_email=args.enable_emaillog,
            enable_sentry=args.enable_sentrylog,
            level=args.log_level,
        )


class NoExcTextFormatter(logging.Formatter):
    """
    Formats records identically to logging.Formatter but does *not* append
    record.exc_text.
    """

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        return s


class ExtraFilter(logging.Filter):
    """
    Attaches extra fields to log records if not already there, typically used
    to ensure that a log record has certain fields by default once it reaches
    a handler, e.g.:

    .. code:: python

        logging.config.dictConfig({
        ...
        'filters': {
            'defaults': {
                '()': 'chronicle.ExtraFilter',
                'guru_id': '-',
            },
        ...
        })

    Adding a 'defaults' filter to a handler ensures guru_id will be defaulted
    to  '-' if not otherwise set.
    """

    def __init__(self, **extra):
        super(ExtraFilter, self).__init__()
        self.extra = extra

    def filter(self, record):
        for k, v in self.extra.iteritems():
            if not hasattr(record, k):
                setattr(record, k, v)
        return True


class LogVersionFilter(logging.Filter):
    def __init__(self, package, key='version'):
        super(LogVersionFilter, self).__init__()
        self.package = package
        self.key = key

    def filter(self, record):
        try:
            pkg = importlib.import_module(self.package)
            setattr(record, self.key, pkg.__version__)
        except:
            pass
        return True


class LogExtraFilter(logging.Filter):
    def __init__(self, **extra):
        super(LogExtraFilter, self).__init__()
        self.extra = extra

    def filter(self, record):
        for k, v in self.extra.iteritems():
            setattr(record, k, v)
        return True
