from __future__ import absolute_import
from flask import request
from flask.signals import got_request_exception
from errormator_client import make_errormator_middleware
from errormator_client.ext.general import gather_data


def log_exception(sender, exception, **extra):
    errormator_client = request.environ['errormator.client']
    gather_data(errormator_client, request.environ, gather_slowness=False,
                gather_logs=False)


def add_errormator(app, config):
    """
        Adds Errormator to Flask,
        
        first looks at config var, then tries to read ERRORMATOR from app.config 
    """
    if not config:
        config = app.config.get('ERRORMATOR')
    if not config:
        raise Exception("Couldn't find Errormator config")
    app.wsgi_app = make_errormator_middleware(app.wsgi_app, config)
    got_request_exception.connect(log_exception, app)
    return app
