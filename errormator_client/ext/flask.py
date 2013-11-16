from __future__ import absolute_import
from flask import request
from flask.signals import got_request_exception, request_started
from errormator_client.client import make_errormator_middleware, get_config
from errormator_client.ext.general import gather_data

import logging

log = logging.getLogger(__name__)


def log_exception(sender, exception, **extra):
    errormator_client = request.environ['errormator.client']
    gather_data(errormator_client, request.environ, gather_slowness=False,
                gather_logs=False)


def populate_post_vars(sender, **extra):
    """
    This is to handle iterated wsgi.input by werkzeug when we create webob obj 
    parsing environ
    """
    if request.method in ['POST', 'PUT']:
        request.environ['errormator.post_vars'] = request.form
    else:
        request.environ['errormator.post_vars'] = {}


def add_errormator(app, config=None):
    """
        Adds Errormator to Flask,

        first looks at config var,then tries to read ERRORMATOR from app.config
    """
    if not config and app.config.get('ERRORMATOR'):
        config = app.config.get('ERRORMATOR')
    if config:
        pass
    else:
        config = {}
    app.wsgi_app = make_errormator_middleware(app.wsgi_app, config)
    request_started.connect(populate_post_vars, app)
    got_request_exception.connect(log_exception, app)
    return app
