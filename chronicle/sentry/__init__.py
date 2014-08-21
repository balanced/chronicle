from __future__ import unicode_literals
import logging

from raven import processors


class Formatter(logging.Formatter):
    """
    Formats records identically to `logging.Formatter` but does *not* append
    `record.exc_text`.
    """

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        return s


class Filter(logging.Filter):
    """
    Captures, encodes and attaches exception as a sentry message and attaches
    it the logging record.

    You can then reference the encoded sentry message in a loggig formatter:

        %(sentry)s

    """

    client_cls = None

    def __init__(self, project, **options):
        self.extra = options.pop('extra', [])
        self.client = self.client_cls(project=project, **options)

    def filter(self, record):
        if not record.exc_info:
            # ignore
            return False
        try:
            extra = dict(
                (k, getattr(record, k))
                for k in self.extra if hasattr(record, k)
            )
            msg = self.client.build_msg(
                'raven.events.Exception',
                exc_info=record.exc_info,
                extra=extra,
            )
            encoded = self.client.encode(msg)
            record.sentry = encoded
        except:
            # ignore
            return False
        return True


class SanitizeProcessor(processors.SanitizePasswordsProcessor):

    FIELDS = frozenset([
        'password', 'secret', 'card_number', 'account_number',
        'security_code', 'ssn', 'ssn_last_4', 'ssn_last4', 'tax_id',
    ])


class BalancedSentryProcessor(SanitizeProcessor):

    pass
