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

.. warning::
    Errormator client 0.5 is **BACKWARDS INCOMPATIBLE** with previous versions,
    please read integration documentation.
    By default configuration is expected to be stored in separate ini file. 

Main Documentation location
===========================

Errormator developer documentation contains most up to date information, 
including implementation guides in popular python web frameworks. 

https://errormator.com/page/api/main
    
Usage
=====

Before you can use the client inside your application you first need to 
navigate to the directory that stores your application configuration and issue
following command::

    $ENV/bin/python/errormator_client makeini errormator.ini

Usage (example for pyramid or other WSGI pipeline compatible solutions like Zope):

In your INI file you need to add::

    [filter:errormator_client]
    use = egg:errormator_client
    errormator.config_path = %(here)s/errormator.ini #optional if you don't want to set ERRORMATOR_INI env var

    [pipeline:main]
    pipeline =
        .....your other pipeline entries ....
        errormator_client
        app_name

To minimize configuration complexity, the client by default will look for 
ERRORMATOR_INI environment variable that will supply absolute path 
to config file.

for pylons app you can modify config/middleware.py:
import the callable and add this lines::

    #exception gathering
    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
      
    app = make_errormator_middleware(app,config)

and add in your ini::

    errormator.config_path = %(here)s/errormator.ini #optional if you don't want to set ERRORMATOR_INI env var

       
Errormator client provides slow call and datastore timing capabilities, 
currently out of the box folliwing libraries are supported:

* urllib
* urllib2
* urllib3
* requests
* pysolr
* httplib
* most used dbapi2 drivers
* mongodb
* mako templates
* jinja2 templates
* django templates

If for some reason you want to disable timing of specific library - just set the 
time value to false.

Configuring errormator and django
=================================

For django framework there is separate compatible middleware provided.

Modify your settings file to contain::

    import errormator_client.client as e_client
    ERRORMATOR = e_client.get_config()

Additionally middleware stack needs to be modified with additional middleware::

    MIDDLEWARE_CLASSES = (
        'errormator_client.django_middleware.ErrormatorMiddleware',
        'django.middleware.common.CommonMiddleware',
        ...


Please note that errormator middleware should be the first one in stack to 
function properly.

Run your django app providing ERRORMATOR_INI env variable containing absolute 
path to your config file.

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
        from errormator_client.timing import get_local_storage, local_timing
        errormator_storage = get_local_storage(local_timing)
        stats, slow_calls = errormator_storage.get_thread_stats()
        traceback = get_current_traceback(skip=1, show_hidden_frames=True, ignore_system_exceptions=True)
        request.environ['errormator.client'].py_report(request.environ, traceback, message=None,http_status=500, request_stats=stats)
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