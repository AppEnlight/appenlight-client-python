from appenlight_client.utils import import_module
from appenlight_client.timing import _e_trace

import logging

log = logging.getLogger(__name__)

# http://www.python.org/dev/peps/pep-0249/

ignore_set = frozenset()


def general_factory(slow_call_name, subtype):
    def gather_args(*args, **kwargs):
        return {'type': 'sql', 'subtype': subtype,
                'statement': slow_call_name,
                'count': False,
                'ignore_in': ignore_set}

    return gather_args


def gather_query_factory(subtype):
    def gather_query(query, *args, **kwargs):
        return {'type': 'sql', 'subtype': subtype, 'statement': query,
                'parameters': args,
                'count': True,
                'ignore_in': ignore_set}

    return gather_query


def add_timing(module_name, min_duration=0.1):
    module = import_module(module_name)
    if not module:
        return

    class CursorWrapper(object):
        def __init__(self, instance, module_name):
            object.__setattr__(self, '_e_db_module_name', module_name)
            object.__setattr__(self, '_e_db_fetch',
                               general_factory('fetch', module_name))
            object.__setattr__(self, '_e_db_fetchmany',
                               general_factory('fetchmany', module_name))
            object.__setattr__(self, '_e_db_fetchall',
                               general_factory('fetchall', module_name))
            object.__setattr__(self, '_e_db_nextset',
                               general_factory('nextset', module_name))
            object.__setattr__(self, '_e_db_next',
                               general_factory('next', module_name))
            object.__setattr__(self, '_e_db_query',
                               gather_query_factory(module_name))
            object.__setattr__(self, '_e_object', instance)

        #        def callproc(self, *args, **kwargs):
        #            return _e_trace(self._e_db_query, min_duration,
        #                            self._e_object.callproc, *args, **kwargs)

        def execute(self, *args, **kwargs):
            return _e_trace(self._e_db_query, min_duration,
                            self._e_object.execute, *args, **kwargs)

        def executemany(self, *args, **kwargs):
            return _e_trace(self._e_db_query, min_duration,
                            self._e_object.executemany, *args, **kwargs)

        def fetch(self, *args, **kwargs):
            return _e_trace(self._e_db_fetch, min_duration,
                            self._e_object.fetch, *args, **kwargs)

        def fetchmany(self, *args, **kwargs):
            return _e_trace(self._e_db_fetchmany, min_duration,
                            self._e_object.fetchmany, *args, **kwargs)

        def fetchall(self, *args, **kwargs):
            return _e_trace(self._e_db_fetchall, min_duration,
                            self._e_object.fetchall, *args, **kwargs)

        def nextset(self, *args, **kwargs):
            return _e_trace(self._e_db_nextset, min_duration,
                            self._e_object.nextset, *args, **kwargs)

        def next(self, *args, **kwargs):
            return _e_trace(self._e_db_next, min_duration,
                            self._e_object.next, *args, **kwargs)

        def __setattr__(self, name, value):
            return setattr(self._e_object, name, value)

        def __getattr__(self, name):
            return getattr(self._e_object, name)

        def __iter__(self):
            return iter(self._e_object)

        def __call__(self, *args, **kwargs):
            return self._e_object(*args, **kwargs)

    class TimerWrapper(object):

        def __init__(self, instance, module_name):
            # assign to superclass or face the infinite recursion consequences
            object.__setattr__(self, '_e_db_module_name', module_name)
            object.__setattr__(self, '_e_db_commit',
                               general_factory('COMMIT', module_name))
            object.__setattr__(self, '_e_db_rollback',
                               general_factory('ROLLBACK', module_name))
            object.__setattr__(self, '_e_object', instance)

        def cursor(self, *args, **kwargs):
            result = CursorWrapper(self._e_object.cursor(*args, **kwargs),
                                   self._e_db_module_name)
            return result

        def commit(self, *args, **kwargs):
            return _e_trace(self._e_db_commit, min_duration,
                            self._e_object.commit, *args, **kwargs)

        def rollback(self, *args, **kwargs):
            return _e_trace(self._e_db_rollback, min_duration,
                            self._e_object.rollback, *args, **kwargs)

        def __setattr__(self, name, value):
            return setattr(self._e_object, name, value)

        def __getattr__(self, name):
            return getattr(self._e_object, name)

        def __iter__(self):
            return iter(self._e_object)

        def __call__(self, *args, **kwargs):
            return self._e_object(*args, **kwargs)

    class Wrapper(object):

        _e_attached_wrapper = True

        def __init__(self, conn_callable, module_name):
            # assign to superclass or face the infinite recursion consequences
            object.__setattr__(self, '_e_module_name', module_name)
            object.__setattr__(self, '_e_object', conn_callable)
            object.__setattr__(self, '_e_db_connect',
                               general_factory('CONNECT', module_name))

        def __setattr__(self, name, value):
            return setattr(self._e_object, name, value)

        def __getattr__(self, name):
            return getattr(self._e_object, name)

        def __call__(self, *args, **kwargs):
            return TimerWrapper(_e_trace(self._e_db_connect, min_duration / 2.0,
                                         self._e_object, *args, **kwargs),
                                self._e_module_name)

    if module_name == 'psycopg2':
        # psycopg2 does a weird type check when someone does
        # psycopg2.extensions.register_type
        # we need to go around this issue by monkey patching it
        import psycopg2.extensions

        org_register_type = psycopg2.extensions.register_type

        def new_register_type(obj, scope=None):
            attached_scope = getattr(scope, '_e_object', scope)
            if attached_scope:
                return org_register_type(obj, attached_scope)
            return org_register_type(obj)

        psycopg2.extensions.register_type = new_register_type
    if module_name == 'sqlite3':
        if hasattr(module.dbapi2.connect, '_e_attached_wrapper'):
            return
        module.dbapi2.connect = Wrapper(module.dbapi2.connect, module_name)
        module.connect = Wrapper(module.connect, module_name)
    elif module_name == 'pg8000':
        if hasattr(module.DBAPI.connect, '_e_attached_wrapper'):
            return
        module.DBAPI.connect = Wrapper(module.DBAPI.connect, module_name)
    else:
        if hasattr(module.connect, '_e_attached_wrapper'):
            return
        module.connect = Wrapper(module.connect, module_name)
