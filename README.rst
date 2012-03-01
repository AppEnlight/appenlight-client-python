errormator_client
=================
usage (example for pyramid):

in your ini add::


    #exception gathering
    [filter:errormator_client]
    use = egg:errormator_client#errormator
    debug = false
    errormator = true
    errormator.server_url = https://api.errormator.com
    errormator.api_key = YOUR_API_KEY
    #404 gathering
    errormator.report_404 = true

    [pipeline:main]
        pipeline =
        weberror
        errormator_client
        .....your pipeline.... 
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

    errormator.server_name - identifier for Instance/Server Name your application is running on (default: auto determined fqdn of server)
    errormator.timeout - connection timeout when communicating with API
    errormator.reraise_exceptions - reraise exceptions when wsgi catches exception
    errormator.slow_requests - record slow requests in application (needs to be enabled for slow datastore recording)
    errormator.logging - enable hooking to application loggers
    errormator.logging.level - minimum log level for log capture
    errormator.datastores - enable query execution tracking for various datastore layers 
    errormator.slow_request_time - (float/int) time in seconds after request is considered being slow (default 30)
    errormator.slow_query_time - (float/int) time in seconds after datastore sql query is considered being slow (default 7)
    errormator.datastores.sqlalchemy = default true - tries to enable sqlalchemy query logging
    errormator.report_404 - enables 404 error logging (default False)
    errormator.report_errors - enables 500 error logging (default True)
    errormator.buffer_flush_interval - how often send data to mothership Errormator (default 5)
    errormator.force_send - send all data after request is finished - handy for crons or other voliatile applications

errormator_client is BSD licensed, consult LICENSE for details. 

Sensitive data filtering
========================
The client by default blanks out COOKIE,POST,GET for keys like:
'password','passwd','pwd','auth_tkt'

This behaviour can be altered to filter all kinds of data from the structures
that get sent to the server by passing dotted module name in configuration::

    errormator.filter_callable = foo.bar.baz:callable_name

example:

    def callable_name(structure, section=None):
        structure['request']['SOMEVAL'] = '***REMOVED***'
        return structure

Errormator will try to import foo.bar.baz and use callable_name as the function
that accepts parameters (structure, section) and returns altered data structure.

Installation and Setup
======================

Install ``errormator_client`` using easy_install::

    easy_install errormator_client