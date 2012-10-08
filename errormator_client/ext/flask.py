from __future__ import absolute_import
from flask import request
from flask.signals import got_request_exception
from errormator_client.client import make_errormator_middleware, get_config
from errormator_client.ext.general import gather_data

import logging

log = logging.getLogger(__name__)

def log_exception(sender, exception, **extra):
    errormator_client = request.environ['errormator.client']
    gather_data(errormator_client, request.environ, gather_slowness=False,
                gather_logs=False)


def add_errormator(app, config=None):
    """
        Adds Errormator to Flask,
        
        first looks at config var, then tries to read ERRORMATOR from app.config 
    """
    if not config:
        config = app.config.get('ERRORMATOR')
    if not config:
        config = get_config()
    app.wsgi_app = make_errormator_middleware(app.wsgi_app, config)
    got_request_exception.connect(log_exception, app)
    return app
