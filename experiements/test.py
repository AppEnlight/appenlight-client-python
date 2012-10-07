import datetime
import logging
import socket
import pkg_resources
import time
from errormator_client import client, make_errormator_middleware
from errormator_client.exceptions import get_current_traceback
from errormator_client.logger import register_logging
from errormator_client.wsgi import ErrormatorWSGIWrapper


fname = pkg_resources.resource_filename('errormator_client',
                                        'templates/default_template.ini')
timing_conf = client.get_config(path_to_config=fname)
for k,v in timing_conf.iteritems(): 
    if 'errormator.timing' in k:
        timing_conf[k] = 0.000001

client.Client(config=timing_conf)
from errormator_client.timing import local_timing

result = local_timing._errormator.get_slow_calls()
print len(result)
