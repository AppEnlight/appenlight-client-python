appenlight_client
=================

.. image:: https://appenlight.com/static/images/logos/python_small.png
   :alt: Python Logo
  
.. image:: https://appenlight.com/static/images/logos/pyramid_small.png
   :alt: Pyramid Logo
  
.. image:: https://appenlight.com/static/images/logos/flask_small.png
   :alt: Flask Logo
     
.. image:: https://appenlight.com/static/images/logos/django_small.png
   :alt: Django Logo

Installation and Setup
======================

Install ``appenlight_client`` using pip::

    pip install appenlight-client

Main Documentation location
===========================

Appenlight developer documentation contains most up to date information,
including implementation guides in popular python web frameworks. 

https://appenlight.com/page/api/main
    
Usage
=====

Before you can use the client inside your application you first need to 
navigate to the directory that stores your application configuration and issue
following command::

    $ENV/bin/python/appenlight_client makeini appenlight.ini

Usage (example for pyramid or other WSGI pipeline compatible solutions like Zope):

In your INI file you need to add::

    [filter:appenlight_client]
    use = egg:appenlight_client
    appenlight.config_path = %(here)s/appenlight.ini #optional if you don't want to set APPENLIGHT_INI env var

    [pipeline:main]
    pipeline =
        .....your other pipeline entries ....
        appenlight_client
        app_name

To minimize configuration complexity, the client by default will look for 
APPENLIGHT_INI environment variable that will supply absolute path
to config file.

for pylons app you can modify config/middleware.py:
import the callable and add this lines::

    #exception gathering
    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
      
    app = make_appenlight_middleware(app,config)

and add in your ini::

    appenlight.config_path = %(here)s/appenlight.ini #optional if you don't want to set APPENLIGHT_INI env var

       
Appenlight client provides slow call and datastore timing capabilities,
currently out of the box folliwing libraries are supported:

* most used dbapi2 drivers
* django templates
* httplib
* jinja2 templates
* mongodb
* mako templates
* pysolr
* requests
* urllib
* urllib2
* urllib3 

If for some reason you want to disable timing of specific library - just set the 
time value to false.

Configuring appenlight and django
=================================

For django framework there is separate compatible middleware provided.

Modify your settings file to contain::

    import appenlight_client.client as e_client
    APPENLIGHT = e_client.get_config()

Additionally middleware stack needs to be modified with additional middleware::

    MIDDLEWARE_CLASSES = (
        'appenlight_client.django_middleware.AppenlightMiddleware',
        'django.middleware.common.CommonMiddleware',
        ...


Please note that appenlight middleware should be the first one in stack to
function properly.

Run your django app providing APPENLIGHT_INI env variable containing absolute
path to your config file.

Changing default scaffold configuration in Pyramid Web Framework
================================================================

Default scaffolds in pyramid 1.3 have a section called *[app:main]* - 
appenlight client expects that you are using *wsgi pipeline* instead to
position itself in it.

The easiest way to accomplish that is to alter your configuration file to look 
like this::

    [app:main] becomes [app:yourappname] 

and inside your configuration, **above [server:main]** directive following 
directive should appear::

    [pipeline:main]
    pipeline =
        ... your other middleware you may have ...
        appenlight_client
        yourappname
 


Exception views in Pyramid Web Framework and Appenlight
=======================================================

Pyramid uses exception views to serve nice html templates when exception occurs.
Unfortunately this means that exception is handled BEFORE it reaches appenlight's
middleware so 500 error data will never get sent to appenlight.

This is how you can handle error handling inside your error_view::

    def error_view(exc, request):
        from appenlight_client.exceptions import get_current_traceback
        from appenlight_client.timing import get_local_storage, local_timing
        appenlight_storage = get_local_storage(local_timing)
        stats, slow_calls = appenlight_storage.get_thread_stats()
        traceback = get_current_traceback(skip=1, show_hidden_frames=True, ignore_system_exceptions=True)
        request.environ['appenlight.client'].py_report(request.environ, traceback, message=None,http_status=500, request_stats=stats)
        request.response.status = 500
        return {}

Sensitive data filtering
========================
The client by default blanks out COOKIE,POST,GET for keys like:
'password','passwd','pwd','auth_tkt'

This behaviour can be altered to filter all kinds of data from the structures
that get sent to the server by passing dotted module name in configuration::

    appenlight.filter_callable = foo.bar.baz:callable_name

example::

    def callable_name(structure, section=None):
        structure['request']['SOMEVAL'] = '***REMOVED***'
        return structure

Appenlight will try to import foo.bar.baz and use callable_name as the function
that accepts parameters (structure, section) and returns altered data structure.

Please note that this functionality can be used to alter things like appenlight
grouping  mechanism - you can set this variable based on values present in structure 
generated by the client 

appenlight_client is BSD licensed, consult LICENSE for details.

**client source**: https://github.com/AppEnlight/appenlight-client-python