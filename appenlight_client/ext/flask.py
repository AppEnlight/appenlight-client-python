from __future__ import absolute_import
from flask import request
from flask.signals import got_request_exception, request_started
from appenlight_client.client import make_appenlight_middleware_with_client
from appenlight_client.ext.general import gather_data
from appenlight_client.utils import fullyQualifiedName

import logging

log = logging.getLogger(__name__)


def log_exception(sender, exception, **extra):
    appenlight_client = request.environ['appenlight.client']
    gather_data(appenlight_client, request.environ, gather_slowness=False,
                gather_logs=False)


def populate_post_vars(sender, **extra):
    """
    This is to handle iterated wsgi.input by werkzeug when we create webob obj
    parsing environ
    """
    try:
        view_callable = sender.view_functions[request.endpoint]
        request.environ['appenlight.view_name'] = fullyQualifiedName(view_callable)
    except Exception:
        pass
    if request.method in ['POST', 'PUT']:
        request.environ['appenlight.post_vars'] = request.form
    else:
        request.environ['appenlight.post_vars'] = {}


def add_appenlight_with_client(app, config=None):
    """
        Adds Appenlight to Flask,

        first looks at config var,then tries to read APPENLIGHT from app.config
    """
    if not config and app.config.get('APPENLIGHT'):
        config = app.config.get('APPENLIGHT')
    if config:
        pass
    else:
        config = {}
    app.wsgi_app, client = make_appenlight_middleware_with_client(app.wsgi_app,
                                                                  config)
    request_started.connect(populate_post_vars, app)
    got_request_exception.connect(log_exception, app)
    return app, client


def add_appenlight(app, config=None):
    """
    Bw. compatible API
    """
    app, client = add_appenlight_with_client(app, config)
    return app
