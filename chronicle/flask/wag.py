from __future__ import unicode_literals

import json
import logging

from flask import has_request_context
from flask import request as current_request


def to_json(dikt):
    return json.dumps(dikt)


class LogGuruFilter(logging.Filter):
    def __init__(self, default='-'):
        super(LogGuruFilter, self).__init__()
        self.default = default

    def filter(self, record):
        if has_request_context():
            record.guru_id = current_request.guru_id
        else:
            record.guru_id = self.default
        return True


class LogHTTPStatusFilter(logging.Filter):
    def __init__(self, include_codes):
        super(LogHTTPStatusFilter, self).__init__()
        self.include_codes = include_codes

    def filter(self, record):
        if not record.exc_info or not has_request_context():
            return True
        ex = record.exc_info[1]
        if not isinstance(ex, HTTPException):
            return True
        return ex.code in self.include_codes


class RequestLogger(object):

    def __init__(self, logger_name, masked_fields, mask='X'):
        self.logger = logging.getLogger(logger_name)
        self.masked_fields = masked_fields
        self.mask = mask

    def _mask_fields(self, payload):
        if not isinstance(payload, dict):
            return payload
        masked_payload = {}
        for k, v in payload.iteritems():
            if k in self.masked_fields:
                if self.mask is None:
                    continue
                if isinstance(v, basestring):
                    # NOTE: hide masked field length
                    v = self.mask * 8
                else:
                    v = self.mask
            elif isinstance(v, dict):
                v = self._mask_fields(v)
            masked_payload[k] = v
        return masked_payload

    def log(self, response):
        raise NotImplementedError()


class ClientRequestLogger(RequestLogger):

    def _filter_body(self, response):
        return True

    def log(self, response):
        data = {}

        # request
        request = response.request
        data['request'] = {
            'url': request.url,
            'method': request.method,
            }
        data['request']['headers'] = request.headers.items()

        # response
        data['response'] = {
            'status': response.status_code,
            'headers': response.headers.items(),
            }
        if self._filter_body(response):
            if hasattr(response, 'data'):
                data['response']['data'] = response.data
            elif hasattr(response, 'content'):
                data['response']['body'] = response.content

        # guru_id
        if GuruRequestMixin.guru_id_header in request.headers:
            guru_id = request.headers[GuruRequestMixin.guru_id_header]
            data['guru_id'] = guru_id

        raw = to_json(data)
        self.logger.info(raw)


class ServerRequestLogger(RequestLogger):

    def __init__(self,
                 logger_name,
                 masked_fields,
                 mask='X',
                 no_response_body=None,
                 ):
        super(ServerRequestLogger, self).__init__(
            logger_name, masked_fields, mask='X'
        )
        # By default, don't log response body for all 2XX
        # responses. no_response_body can be a mixed list of either status
        # codes or tuples of the form ('METHOD', status_code).
        if no_response_body is None:
            no_response_body = range(200, 300)
        self.no_response_body = set()
        for r in no_response_body:
            if isinstance(r, (int, str)):
                self.no_response_body.add(str(r))
            elif isinstance(r, tuple):
                self.no_response_body.add(tuple(str(p) for p in r))
            else:
                raise TypeError('no_response_body must be a list of ints, '
                                'strs, or tuples')

    def _should_include_response_body(self, status, method):
        # Status is something like '200 OK'
        status_code = status.split()[0]
        method_and_status = (method, status_code)

        return (status_code not in self.no_response_body and
                method_and_status not in self.no_response_body)

    def log(self, response):
        data = {}

        # request
        data['request'] = {
            'url': current_request.url,
            'method': current_request.method,
        }
        try:
            if getattr(current_request, 'payload', None):
                payload = self._mask_fields(current_request.payload)
                data['request']['payload'] = payload
        except Exception:
            pass
        data['request']['headers'] = current_request.headers.to_list(
            charset='utf-8'
        )

        # user_guid
        user_guid = None
        if (hasattr(current_request, 'user') and
                hasattr(current_request.user, 'guid')):
            user_guid = current_request.user.guid
        data['user_guid'] = user_guid

        # guru_id
        data['guru_id'] = current_request.guru_id

        # response
        content_type = response.headers['Content-Type']
        data['response'] = {
            'status': response.status,
            'headers': response.headers.to_list(charset='utf-8')
        }
        if (self._should_include_response_body(response.status,
                                               current_request.method) and
                getattr(response, 'response', None) and
                (content_type in ['application/json', 'application/xml']
                 or content_type.startswith('text/'))):
            body = response.response
            if (isinstance(body, list)
                and all(isinstance(x, basestring) for x in body)):
                body = [c.decode('utf8') for c in body]
                data['response']['body'] = ''.join(body)

        raw = to_json(data)
        self.logger.info(raw)
