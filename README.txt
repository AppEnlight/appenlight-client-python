errormator_client
============
usage (example for pyramid):

in your ini add:

[filter:errormator_client]
use = egg:errormator_client#error_catcher
debug = false
errormator = true
errormator.server_url = http://api.errormator.com
errormator.api_key = YOUR_API_KEY
errormator.server = Instance/Server Name

[pipeline:main]
pipeline =
    errormator_client
    .....your pipeline.... 
    app_name


for pylons app you can modify config/middleware.py:
in place of normal error middleware add:

if asbool(config.get('errormator')):    
    cb = ErrormatorCatcher(app, config)

and add in your ini:
errormator = true
errormator.server_url = http://api.errormator.com
errormator.api_key = YOUR_API_KEY
errormator.server = Instance/Server Name


errormator_client is BSD licensed, consult LICENSE for details. 

Installation and Setup
======================

Install ``errormator_client`` using easy_install::

    easy_install errormator_client