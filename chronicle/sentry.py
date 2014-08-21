from __future__ import unicode_literals
import logging

from flask import request, has_request_context
from raven import Client as BaseClient, processors
from raven.handlers.logging import SentryHandler
from raven.utils.wsgi import get_current_url, get_environ



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

    def __init__(self, project, **options):
        self.extra = options.pop('extra', [])
        self.client = Client(project=project, **options)

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


class WSGIRequestProcessor(processors.Processor):

    def get_data(self, data, **kwargs):
        if 'sentry.interfaces.Http' in data or not has_request_context():
            return
        environ = request.environ
        headers = dict(request.headers)
        guru_key = getattr(request, 'guru_id_header', None)
        if guru_key and guru_key not in headers:
            headers[guru_key] = request.guru_id

        request_data = {
            'sentry.interfaces.Http': {
                'method': environ.get('REQUEST_METHOD'),
                'url': get_current_url(environ, strip_querystring=True),
                'query_string': environ.get('QUERY_STRING'),
                # TODO
                # 'data': environ.get('wsgi.input'),
                'headers': headers,
                'env': dict(get_environ(environ)),
                'form': dict(request.form),
            }
        }
        data.update(request_data)


class Client(BaseClient):

    def __init__(self, dsn=None, **options):
        processors = list(options.pop('processors', []))
        processors.append('sterling.log.sentry.BalancedSentryProcessor')
        processors.append('sterling.log.sentry.WSGIRequestProcessor')
        super(Client, self).__init__(
            dsn=dsn, processors=processors, **options
        )
