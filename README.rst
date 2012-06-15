errormator_client
=================

.. image:: https://errormator.com/static/images/logos/python_small.png
   :alt: Python Logo
  
.. image:: https://errormator.com/static/images/logos/pyramid_small.png
   :alt: Pyramid Logo
  
.. image:: https://errormator.com/static/images/logos/flask_small.png
   :alt: Flask Logo
     
.. image:: https://errormator.com/static/images/logos/django_small.png
   :alt: Django Logo

Installation and Setup
======================

Install ``errormator_client`` using pip::

    pip install errormator-client

Main Documentation location
===========================

Errormator developer documentation contains most up to date information

https://errormator.com/page/api/main
    
Usage
=====

usage (example for pyramid or other WSGI pipeline compatible solutions like Zope):

In your INI file you need to add::


    [filter:errormator_client]
    use = egg:errormator_client
    debug = false
    errormator = true
    errormator.server_url = https://api.errormator.com
    errormator.api_key = YOUR_API_KEY
    #404 gathering
    errormator.report_404 = true
    ... other config vars go here....

    [pipeline:main]
        pipeline =
        errormator_client
        .....your other pipeline entries .... 
        app_name

for pylons app you can modify config/middleware.py:
import the callable and add this lines::

    #exception gathering
    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
      
    app = make_errormator_middleware(app,config)

and add in your ini::

    errormator = true
    errormator.server_url = https://api.errormator.com
    errormator.api_key = YOUR_API_KEY
    errormator.report_404 = true


additional config variables you can set in config object::

    errormator.server_name - identifier for Instance/Server Name your application is running on 
    (default: auto determined fqdn of server)
    errormator.timeout - connection timeout when communicating with API
    errormator.reraise_exceptions - reraise exceptions when wsgi catches exception
    errormator.slow_requests - record slow requests in application (needs to be enabled for slow datastore recording)
    errormator.logging - enable hooking to application loggers
    errormator.logging.level - minimum log level for log capture
    errormator.logging_on_error - send logs only from erroneous/slow requests (default false)
    errormator.datastores - enable query execution tracking for various datastore layers 
    errormator.slow_request_time - (float/int) time in seconds after request is considered being slow 
    (default 30)
    errormator.slow_query_time - (float/int) time in seconds after datastore sql query is considered being slow (default 7)
    errormator.datastores.sqlalchemy = default true - tries to enable sqlalchemy query logging
    errormator.report_404 - enables 404 error logging (default False)
    errormator.report_errors - enables 500 error logging (default True)
    errormator.buffer_flush_interval - how often send data to mothership Errormator (default 5)
    errormator.force_send - send all data after request is finished - handy for crons or other voliatile applications
    errormator.environ_keys_whitelist - list of addotonal keywords that should be grabbed from environ object
    (can be string with comma separated list of words in lowercase)
    (by default client will always send following info 'REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE' 
    + all keys that start with HTTP* this list be extended with additional keywords set in config)
    errormator.request_keys_blacklist - list of keywords that should be blanked from request object
    (can be string with comma separated list of words in lowercase)
    (by default client will always blank keys that contain following words 
    'password', 'passwd', 'pwd', 'auth_tkt', 'secret', 'csrf', this list be extended with additional keywords set in config)
    errormator.log_namespace_blacklist = list of namespaces that should be ignores when gathering log entries
    (can be string with comma separated list of namespaces
    by default the client ignores own entries: errormator_client.client)

Configuring errormator and django
=================================

For django framework there is separate compatible middleware provided.

Modify your settings file to contain::

    ERRORMATOR = {
            'errormator': True,
            'errormator.server_url': 'https://api.errormator.com',
            'errormator.api_key': 'YOUR_API_KEY',
            'errormator.catch_callback': False,
            'errormator.report_404': True,
            'errormator.logging': True,
            'errormator.logging.level': 'WARNING',
            'errormator.slow_request': True,
            'errormator.slow_request.time': 30,
            'errormator.slow_request.sqlalchemy': True,
            'errormator.slow_query.time': 7,
            'errormator.buffer_flush_time': 5,
              }

Additionally middleware stack needs to be modified with additional middleware::

    MIDDLEWARE_CLASSES = (
        'errormator_client.django_middleware.ErrormatorMiddleware',
        'django.middleware.common.CommonMiddleware',
        ...


Please note that errormator middleware should be the first one in stack to 
function properly.

Changing default scaffold configuration in Pyramid Web Framework
================================================================

Default scaffolds in pyramid 1.3 have a section called *[app:main]* - 
errormator client expects that you are using *wsgi pipeline* instead to 
position itself in it.

The easiest way to accomplish that is to alter your configuration file to look 
like this::

    [app:main] becomes [app:yourappname] 

and inside your configuration, **above [server:main]** directive following 
directive should appear::

    [pipeline:main]
    pipeline =
        ... your other middleware you may have ...
        errormator_client
        yourappname
 


Exception views in Pyramid Web Framework and Errormator
=======================================================

Pyramid uses exception views to serve nice html templates when exception occurs.
Unfortunately this means that exception is handled BEFORE it reaches errormator's
middleware so 500 error data will never get sent to errormator.

This is how you can handle error handling inside your error_view::

    def error_view(exc, request):
        from errormator_client.exceptions import get_current_traceback
        traceback = get_current_traceback(skip=1, show_hidden_frames=True, ignore_system_exceptions=True)
        request.environ['errormator.client'].py_report(request.environ, traceback, message=None,http_status=500)
        request.response.status = 500
        return {}

Sensitive data filtering
========================
The client by default blanks out COOKIE,POST,GET for keys like:
'password','passwd','pwd','auth_tkt'

This behaviour can be altered to filter all kinds of data from the structures
that get sent to the server by passing dotted module name in configuration::

    errormator.filter_callable = foo.bar.baz:callable_name

example::

    def callable_name(structure, section=None):
        structure['request']['SOMEVAL'] = '***REMOVED***'
        return structure

Errormator will try to import foo.bar.baz and use callable_name as the function
that accepts parameters (structure, section) and returns altered data structure.

Please note that this functionality can be used to alter things like errormator 
grouping  mechanism - you can set this variable based on values present in structure 
generated by the client 

errormator_client is BSD licensed, consult LICENSE for details. 

**client source**: https://bitbucket.org/ergo/errormator_client_python