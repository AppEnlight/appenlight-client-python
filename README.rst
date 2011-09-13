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
import the classes and add this lines::

    #exception gathering
    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
      
    app = make_errormator_middleware(app,config)

and add in your ini::

    errormator = true
    errormator.server_url = https://api.errormator.com
    errormator.api_key = YOUR_API_KEY
    errormator.buffer_flush_time = 60
    errormator.server = Instance/Server Name
    errormator.report_404 = true

Logging API Support
===================
to enable logging support you need to alter your ini file and add more entries
(apart the ones above)::

    errormator.logging = true
    errormator.logging.buffer = 50
    errormator.logging.async = true

first param determines after how many entries errors get flushed to remote service
second param determines if client should make a threaded call

in pylons

It is also possible to send logging messages directly as log function will be 
attached to your environ object::

    request.environ['errormator.log']('FOO','TEST!')

it is also possible to send reports directly from inside of your application::

    request.environ['errormator.report']('TEST Lorem ipsum', False)

Slow Request/Query API Support
==============================
to enable slow api support you need to alter your ini file and add more entries::

    errormator.slow_request = true
    errormator.slow_request.time = 10
    errormator.slow_request.sqlalchemy = true
    errormator.slow_query.time = 10

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