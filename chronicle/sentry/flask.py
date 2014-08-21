from __future__ import unicode_literals

from flask import request, has_request_context
from raven import Client as BaseClient, processors
from raven.utils.wsgi import get_current_url, get_environ

from . import Filter as BaseFilter


class Filter(BaseFilter):
    client_cls = FlaskClient


class WSGIRequestProcessor(processors.Processor):

    def get_data(self, data, **kwargs):
        if 'sentry.interfaces.Http' in data or not has_request_context():
            return
        environ = request.environ
        headers = dict(request.headers)
        guru_key = getattr(request, 'guru_id_header', None)
        if guru_key and guru_key not in headers:
            headers[guru_key] = getattr(request, 'guru_id', None)

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


class FlaskClient(BaseClient):

    def __init__(self, dsn=None, **options):
        processors = list(options.pop('processors', []))
        processors.append('chronicle.sentry.BalancedSentryProcessor')
        processors.append('chronicle.sentry.flask.WSGIRequestProcessor')
        super(FlaskClient, self).__init__(
            dsn=dsn, processors=processors, **options
        )
