from __future__ import absolute_import, unicode_literals

import logging.config
import os

import gunicorn.glogging


class Logger(gunicorn.glogging.Logger):

    def setup(self, cfg):
        if not cfg.logconfig:
            super(Logger, self).setup(cfg)
        else:
            if os.path.exists(cfg.logconfig):
                logconfig = eval(open(cfg.logconfig, 'r').read())
                logging.config.dictConfig(logconfig)
            else:
                raise RuntimeError(
                    "Error: log config '%s' not found" % cfg.logconfig)
