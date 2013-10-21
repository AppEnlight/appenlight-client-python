from decorator import decorator
from errormator_client.utils import import_module, import_from_module
import logging
import inspect
import datetime
import sys
import time
import threading
from operator import itemgetter

# if sys.platform == "win32":
#     # On Windows, the best timer is time.clock()
#     default_timer = time.clock
# else:
#     # On most other platforms the best timer is time.time()
#     default_timer = time.time
default_timer = time.time


class ErrormatorLocalStorage(object):
    def __init__(self):
        self.clear()

    def contains(self, parent, child):
        return (child['start'] >= parent['start'] and
                child['end'] <= parent['end'])

    def get_stack(self):
        data = sorted(self.slow_calls, key=itemgetter('start'))
        stack = []

        for node in data:
            node['parents'] = [n['type'] for n in stack]
            while stack and not self.contains(stack[-1], node):
                stack.pop()
            stack.append(node)
        return data

    def clear(self):
        self.thread_stats = {'main': 0, 'sql': 0, 'nosql': 0, 'remote': 0,
                             'tmpl': 0, 'unknown': 0, 'sql_calls': 0,
                             'nosql_calls': 0, 'remote_calls': 0,
                             'tmpl_calls': 0}
        self.slow_calls = []

    def get_thread_stats(self):
        """ resets thread stats at same time """
        stats = self.thread_stats.copy()
        slow_calls = []
        for row in self.get_stack():
            duration = row['end'] - row['start']
            if row['ignore_in'].intersection(row['parents']):
                # this means that it is used internally in other lib
                continue
            stats[row['type']] += duration
            if row.get('count'):
                stats['%s_calls' % row['type']] += 1
                #count is not needed anymore - we don't want to send this
            row.pop('count', None)
            # if this call was being made inside template - substract duration
            # from template timing
            if 'tmpl' in row['parents'] and row['parents'][-1] != 'tmpl':
                self.thread_stats['tmpl'] -= duration
            if duration >= row['min_duration']:
                slow_calls.append(row)
                # round stats to 5 digits
        for k, v in stats.iteritems():
            stats[k] = round(v, 5)
        return stats, slow_calls


TIMING_REGISTERED = False

local_timing = threading.local()

log = logging.getLogger(__name__)


def get_local_storage(local_timing):
    if not hasattr(local_timing, '_errormator_storage'):
        local_timing._errormator_storage = ErrormatorLocalStorage()
    return local_timing._errormator_storage


def _e_trace(info_gatherer, min_duration, e_callable, *args, **kw):
    """ Used to wrap dbapi2 driver methods """
    start = default_timer()
    result = e_callable(*args, **kw)
    end = default_timer()
    info = {'start': start,
            'end': end,
            'min_duration': min_duration}
    info.update(info_gatherer(*args, **kw))
    errormator_storage = get_local_storage(local_timing)
    errormator_storage.slow_calls.append(info)
    return result


def trace_factory(info_gatherer, min_duration, is_template=False):
    """ Used to auto decorate callables in deco_func_or_method for other 
        non dbapi2 modules """

    def _e_trace(func_errormator, *args, **kw):
        start = default_timer()
        result = func_errormator(*args, **kw)
        end = default_timer()
        info = {'start': start,
                'end': end,
                'min_duration': min_duration}
        info.update(info_gatherer(*args, **kw))
        errormator_storage = get_local_storage(local_timing)
        errormator_storage.slow_calls.append(info)
        return result

    return _e_trace


def time_trace(func_errormator, gatherer, min_duration, is_template=False):
    deco = decorator(trace_factory(gatherer, min_duration), func_errormator)
    deco._e_attached_tracer = True
    if is_template:
        deco._e_is_template = True
    return deco


def register_timing(config):
    timing_modules = ['timing_urllib', 'timing_urllib2', 'timing_urllib3',
                      'timing_requests', 'timing_httplib', 'timing_pysolr',
                      'timing_chameleon', 'timing_mako', 'timing_jinja2',
                      'timing_pymongo', 'timing_redispy', 'timing_memcache',
                      'timing_django_templates']

    for mod in timing_modules:
        min_time = config['timing'].get(mod.replace("timing_", '').lower())
        if min_time is not False:
            log.debug('%s slow time:%s' % (mod, min_time or 'default'))
            e_callable = import_from_module(
                'errormator_client.timing.%s:add_timing' % mod)
            if e_callable:
                if min_time:
                    e_callable(min_time)
                else:
                    e_callable()
        else:
            log.debug('not tracking slow time:%s' % mod)

    db_modules = ['pg8000', 'psycopg2', 'MySQLdb', 'sqlite3', 'oursql',
                  'pyodbc', 'pypyodbc',
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
