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
for k, v in timing_conf.iteritems():
    if 'errormator.timing' in k:
        timing_conf[k] = 0.00000001

client.Client(config=timing_conf)
from errormator_client.timing import local_timing, get_local_storage

import timeit
import jinja2
print 'traced', hasattr(jinja2.Template.render, '_e_attached_tracer')

s = """
template = jinja2.Template('''xxxxx {{1+2}} yyyyyy''')
template.render()
"""
print 'time', timeit.timeit(stmt=s, number=1500, setup="import jinja2")
stats, slow_calls = get_local_storage(local_timing).get_thread_stats()
print 'calls', len(slow_calls)
print 'stats', stats
