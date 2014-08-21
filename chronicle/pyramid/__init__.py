from __future__ import unicode_literals

import logging

import pyramid.httpexceptions
import pyramid.threadlocal


class LogHTTPStatusFilter(logging.Filter):

    base_exc_cls = pyramid.httpexceptions.HTTPException

    def __init__(self, include_codes):
        super(LogHTTPStatusFilter, self).__init__()
        self.include_codes = include_codes

    def filter(self, record):
        request = pyramid.threadlocal.get_current_request()
        if not record.exc_info or not request:
            return True
        ex = record.exc_info[1]
        if not isinstance(ex, self.base_exc_cls):
            return True
        return ex.code in self.include_codes


class LogGuruFilter(logging.Filter):
    def __init__(self, default='-'):
        super(LogGuruFilter, self).__init__()
        self.default = default

    def filter(self, record):
        request = pyramid.threadlocal.get_current_request()
        if request:
            record.guru_id = getattr(request, 'guru_id', self.default)
        else:
            record.guru_id = self.default
        return True
