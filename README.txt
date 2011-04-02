errormator_client
============
usage (example for pyramid):

in your ini add:

#exception gathering
[filter:errormator_client]
use = egg:errormator_client#error_catcher
debug = false
errormator = true
errormator.server_url = https://api.errormator.com
errormator.api_key = YOUR_API_KEY

#404 gathering
[filter:errormator_header_sniffer]
use = egg:errormator_client#header_sniffer
errormator = true
errormator.server_url = https://api.errormator.com
errormator.api_key = YOUR_API_KEY

[pipeline:main]
pipeline =
	weberror
    errormator_client
    .....your pipeline.... 
    app_name


for pylons app you can modify config/middleware.py:
import the classes and add this lines:

#exception gathering
# CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
  
app = ErrormatorCatcher(app, config)
app = ErrormatorHTTPCodeSniffer(app, config)

and add in your ini:
errormator = true
errormator.server_url = https://api.errormator.com
errormator.api_key = YOUR_API_KEY
errormator.server = Instance/Server Name


errormator_client is BSD licensed, consult LICENSE for details. 

Installation and Setup
======================

Install ``errormator_client`` using easy_install::

    easy_install errormator_client