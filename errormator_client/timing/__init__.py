from decorator import decorator
from errormator_client.utils import import_module, import_from_module
import logging
import inspect
import datetime
import sys
import time
import threading

class ErrormatorLocalStorage(object):
        
    def add_slow_call(self, call):
        if not hasattr(self, 'slow_calls'):
            self.slow_calls = []
        self.slow_calls.append(call)
    
    def get_slow_calls(self):        
        calls = getattr(self, 'slow_calls', [])
        self.slow_calls = []
        return calls
    

local_timing = threading.local()

from timeit import Timer

log = logging.getLogger(__name__)

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time

def trace_factory(info_gatherer, min_duration):
    def _e_trace(f, *args, **kw):
        start = default_timer()
        result = f(*args, **kw)
        end = default_timer()
        duration = round(end - start, 4)
        if duration < min_duration:
            return result
        info = {'timestamp':datetime.datetime.fromtimestamp(start),
                'duration':duration}
        info.update(info_gatherer(*args, **kw))
        stack = inspect.stack()
        path = []
        traces = 0
        for frame in stack:
            if frame[3] == '_e_trace':
                traces += 1
                continue
            name = []
            module = inspect.getmodule(frame[0])
            if module:
                name.append(module.__name__)
            elif 'self' in frame[0].f_locals:
                name.append(frame[0].f_locals['self'].__class__.__name__)
                name.append(frame[3])
            elif frame[3] != '<module>':
                name.append(frame[3])
            name = '.'.join(name)            
            if not path or path[-1][0] != name:
                path.append((name, frame[0].f_lineno))
        if traces < 2:
            if not hasattr(local_timing, '_errormator'):
                local_timing._errormator = ErrormatorLocalStorage()
            local_timing._errormator.add_slow_call(info)
        return result
    return _e_trace

def time_trace(f, gatherer, min_duration):
    return decorator(trace_factory(gatherer, min_duration), f)


def register_timing(config):
    timing_modules = ['timing_urllib', 'timing_urllib2', 'timing_urllib3',
                      'timing_requests', 'timing_httplib', 'timing_pysolr']
    for mod in timing_modules:
        min_time = float(config['timing'].get(mod.replace("timing_",''), 0.5))
        log.info('%s slow time:%s' % (mod, min_time))
        if min_time:
            callable = import_from_module('errormator_client.timing.%s:add_timing' % mod)
            callable(min_time)
