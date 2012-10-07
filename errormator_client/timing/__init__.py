from decorator import decorator
from errormator_client.utils import import_module, import_from_module
import logging
import inspect
import datetime
import sys
import time
import threading

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time

class ErrormatorLocalStorage(object):
        
    def add_slow_call(self, call):
        if not hasattr(self, 'slow_calls'):
            self.slow_calls = []
        self.slow_calls.append(call)
    
    def get_slow_calls(self):        
        calls = getattr(self, 'slow_calls', [])
        self.slow_calls = []
        return calls
    
TIMING_REGISTERED = False

local_timing = threading.local()

log = logging.getLogger(__name__)

def stack_inspector():
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
    return path, traces

def _e_trace(info_gatherer, min_duration, callable, *args, **kw):
    """ Used to wrap dbapi2 driver methods """
    start = default_timer()
    result = callable(*args, **kw)
    end = default_timer()
    duration = round(end - start, 4)
    if duration < min_duration:
        return result
    info = {'timestamp':datetime.datetime.utcfromtimestamp(start),
            'duration':duration}
    info.update(info_gatherer(*args, **kw))
    path, traces = stack_inspector()
    # traces >= 2 means that this call was in some other lib thats was timed 
    if traces < 2:
        if not hasattr(local_timing, '_errormator'):
            local_timing._errormator = ErrormatorLocalStorage()
        local_timing._errormator.add_slow_call(info)
    return result

def trace_factory(info_gatherer, min_duration, is_template=False):
    """ Used to auto decorate callables in deco_func_or_method for other 
        non dbapi2 modules """
    
    def _e_trace(f, *args, **kw):
        start = default_timer()
        result = f(*args, **kw)
        end = default_timer()
        duration = round(end - start, 4)
        if duration < min_duration:
            return result
        info = {'timestamp':datetime.datetime.utcfromtimestamp(start),
                'duration':duration}
        info.update(info_gatherer(*args, **kw))
        path, traces = stack_inspector()
        # traces >= 2 means that this call was in some other lib thats was timed
        if traces < 2:
            if not hasattr(local_timing, '_errormator'):
                local_timing._errormator = ErrormatorLocalStorage()
            local_timing._errormator.add_slow_call(info)
        return result 
    return _e_trace

def time_trace(f, gatherer, min_duration, is_template=False):
    deco = decorator(trace_factory(gatherer, min_duration), f)
    deco._e_attached_tracer = True
    if is_template:
        deco._e_is_template = True
    return deco


def register_timing(config):
    timing_modules = ['timing_urllib', 'timing_urllib2', 'timing_urllib3',
                      'timing_requests', 'timing_httplib', 'timing_pysolr',
                      'timing_mako', 'timing_jinja2', 'timing_pymongo',
                      'timing_django_templates']
    
    for mod in timing_modules:
        min_time = config['timing'].get(mod.replace("timing_", '').lower()) 
        if min_time is not False:
            log.debug('%s slow time:%s' % (mod, min_time or 'default'))
            callable = import_from_module('errormator_client.timing.%s:add_timing' % mod)
            if callable:
                if min_time:
                    callable(min_time)
                else:
                    callable()
        else:
            log.debug('not tracking slow time:%s' % mod)
        
    db_modules = ['pg8000', 'psycopg2', 'MySQLdb', 'sqlite3', 'oursql', 'pyodbc',
                  'cx_Oracle', 'kinterbasdb', 'postgresql', 'pymysql']
    import errormator_client.timing.timing_dbapi2 as dbapi2
    for mod in db_modules:
        min_time = config['timing'].get('dbapi2_%s' % mod.lower())
        log.debug('%s dbapi query time:%s' % (mod, min_time or 'default'))
        if min_time is not False:
            if min_time:
                dbapi2.add_timing(mod, min_time)
            else:
                dbapi2.add_timing(mod)
