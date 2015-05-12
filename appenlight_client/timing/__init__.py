from __future__ import absolute_import
import logging
import time
import threading

from appenlight_client.utils import import_from_module
from datetime import datetime, timedelta
from functools import wraps
from operator import itemgetter

default_timer = time.time


class AppenlightLocalStorage(object):

    def __init__(self):
        self.cls_storage = {}

    def contains(self, parent, child):
        return (child['start'] >= parent['start'] and
                child['end'] <= parent['end'])

    def get_stack(self, slow_calls=None):
        if not slow_calls:
            data = sorted(self.slow_calls, key=itemgetter('start'))
        else:
            data = slow_calls
        stack = []

        for node in data:
            while stack and not self.contains(stack[-1], node):
                stack.pop()
            node['parents'] = [n['type'] for n in stack]
            stack.append(node)
        return data

    def get_thread_storage(self, thread=None):
        if thread is None:
            thread = threading.currentThread()
        if thread not in self.cls_storage:
            self.cls_storage[thread] = {'last_updated': datetime.utcnow(),
                                        'logs': []}
            self.clear()
        return self.cls_storage[thread]

    @property
    def logs(self):
        return self.get_thread_storage()['logs']

    @logs.setter
    def logs(self, value):
        self.get_thread_storage()['logs'] = value
        self.get_thread_storage()['last_updated'] = datetime.utcnow()

    @property
    def view_name(self):
        return self.get_thread_storage()['view_name']

    @view_name.setter
    def view_name(self, value):
        self.get_thread_storage()['view_name'] = value
        self.get_thread_storage()['last_updated'] = datetime.utcnow()

    @property
    def slow_calls(self):
        return self.get_thread_storage()['slow_calls']

    @slow_calls.setter
    def slow_calls(self, value):
        self.get_thread_storage()['slow_calls'] = value
        self.get_thread_storage()['last_updated'] = datetime.utcnow()

    @property
    def thread_stats(self):
        return self.get_thread_storage()['thread_stats']

    @thread_stats.setter
    def thread_stats(self, value):
        self.get_thread_storage()['thread_stats'] = value
        self.get_thread_storage()['last_updated'] = datetime.utcnow()

    def clear(self):
        self.thread_stats = {'main': 0, 'sql': 0, 'nosql': 0, 'remote': 0,
                             'tmpl': 0, 'unknown': 0, 'sql_calls': 0,
                             'nosql_calls': 0, 'remote_calls': 0,
                             'tmpl_calls': 0, 'custom': 0, 'custom_calls': 0}
        self.slow_calls = []
        self.view_name = ''

    def get_thread_stats(self):
        """ resets thread stats at same time """
        stats = self.thread_stats.copy()
        slow_calls = []
        for row in self.get_stack():
            duration = row['end'] - row['start']
            if row['ignore_in'].intersection(row['parents']):
                # this means that it is used internally in other lib
                continue
            if row.get('count'):
                stats['%s_calls' % row['type']] += 1
                # if this call was being made inside template - substract duration
            # from template timing
            is_nested_template = 'tmpl' in row['parents']
            is_nested_custom = 'custom' in row['parents']
            if not is_nested_template and not is_nested_custom:
                stats[row['type']] += duration
            if duration >= row['min_duration']:
                slow_calls.append(row)
                # round stats to 5 digits
        for k, v in stats.iteritems():
            stats[k] = round(v, 5)
        return stats, slow_calls

    def cycle_old_data(self, older_than=60):
        boundary = datetime.utcnow() - timedelta(minutes=60)
        for k, v in self.cls_storage.items():
            if v['last_updated'] < boundary or 1:
                del self.cls_storage[k]


TIMING_REGISTERED = False

local_timing = threading.local()

appenlight_storage = AppenlightLocalStorage()

log = logging.getLogger(__name__)


def get_local_storage(local_timing=None):
    return appenlight_storage


def _e_trace(info_gatherer, min_duration, e_callable, *args, **kw):
    """ Used to wrap dbapi2 driver methods """
    start = default_timer()
    result = e_callable(*args, **kw)
    end = default_timer()
    info = {'start': start,
            'end': end,
            'min_duration': min_duration}
    info.update(info_gatherer(*args, **kw))
    appenlight_storage = get_local_storage()
    if len(appenlight_storage.slow_calls) < 1000:
        appenlight_storage.slow_calls.append(info)
    return result


def time_trace(gatherer=None, min_duration=0.1, is_template=False, name=None):
    if gatherer is None:
        if not name:
            name = 'Unnamed callable'

        def gatherer(*args, **kwargs):
            return {'type': 'custom',
                    'subtype': 'user_defined',
                    'statement': name,
                    'parameters': '',
                    'count': True,
                    'ignore_in': set()}

    def decorator(appenlight_callable):
        @wraps(appenlight_callable)
        def wrapper(*args, **kwargs):
            start = default_timer()
            result = appenlight_callable(*args, **kwargs)
            end = default_timer()
            info = {'start': start,
                    'end': end,
                    'min_duration': min_duration}
            info.update(gatherer(*args, **kwargs))
            appenlight_storage = get_local_storage()
            if len(appenlight_storage.slow_calls) < 500:
                appenlight_storage.slow_calls.append(info)
            return result

        # will prevent this wrapper being decorated again
        wrapper._e_attached_tracer = True
        if is_template:
            wrapper._e_is_template = True
        return wrapper

    return decorator


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
                'appenlight_client.timing.%s:add_timing' % mod)
            if e_callable:
                if min_time:
                    e_callable(min_time)
                else:
                    e_callable()
        else:
            log.debug('not tracking slow time:%s' % mod)

    db_modules = ['pg8000', 'psycopg2', 'MySQLdb', 'sqlite3', 'oursql',
                  'pyodbc', 'pypyodbc',
                  'cx_Oracle', 'kinterbasdb', 'postgresql', 'pymysql', 'pymssql']
    import appenlight_client.timing.timing_dbapi2 as dbapi2

    for mod in db_modules:
        min_time = config['timing'].get('dbapi2_%s' % mod.lower())
        log.debug('%s dbapi query time:%s' % (mod, min_time or 'default'))
        if min_time is not False:
            if mod == 'sqlite3' and not min_time:
                continue
            elif min_time:
                dbapi2.add_timing(mod, min_time)
            else:
                dbapi2.add_timing(mod)
