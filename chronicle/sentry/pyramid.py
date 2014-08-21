from __future__ import unicode_literals

import pyramid.threadlocal
from raven import Client as BaseClient, processors
from raven.utils.wsgi import get_current_url, get_environ

from . import Filter as BaseFilter


class Filter(BaseFilter):
    client_cls = PyramidClient


class WSGIRequestProcessor(processors.Processor):

    def get_data(self, data, **kwargs):
        request = pyramid.threadlocal.get_current_request()
        if 'sentry.interfaces.Http' in data or not request:
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
                'form': dict(request.POST),
            }
        }
        data.update(request_data)


class PyramidClient(BaseClient):

    def __init__(self, dsn=None, **options):
        processors = list(options.pop('processors', []))
        processors.append('chronicle.sentry.BalancedSentryProcessor')
        processors.append('chronicle.sentry.pyramid.WSGIRequestProcessor')
        super(PyramidClient, self).__init__(
            dsn=dsn, processors=processors, **options
        )
