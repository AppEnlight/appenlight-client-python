import datetime
import logging
import socket
import pkg_resources
import time
from appenlight_client import client, make_appenlight_middleware
from appenlight_client.exceptions import get_current_traceback
from appenlight_client.logging.logger import register_logging
from appenlight_client.wsgi import AppenlightWSGIWrapper


timing_conf = client.get_config({'appenlight.api_key':'1234'})
for k, v in timing_conf.iteritems():
    if 'appenlight.timing' in k:
        timing_conf[k] = 0.00000001

client.Client(config=timing_conf)
from appenlight_client.timing import local_timing, get_local_storage

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
