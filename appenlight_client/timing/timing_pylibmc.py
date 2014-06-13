from appenlight_client.utils import import_module
from appenlight_client.timing import _e_trace


ignore_set = frozenset()

to_decorate = ['add', 'append', 'cas', 'decr', 'delete', 'delete_multi',
               'get', 'gets', 'get_multi', 'incr', 'prepend', 'replace',
               'set', 'set_multi']


def general_factory(slow_call_name):
    def gather_args(self, *args, **kwargs):
        return {'type': 'nosql', 'subtype': 'memcache-py',
                'count': True,
                'statement': slow_call_name,
                'ignore_in': ignore_set}

    return gather_args


# for m in to_decorate:
#     deco_func_or_method(module, 'Client.%s' % m, time_trace,
#                     general_factory('%s' % m), min_duration)


def add_timing(min_duration=0.1):
    module = import_module('pylibmc')
    if not module:
        return

    class TimerWrapper(object):

        def __init__(self, instance, module_name):
            # assign to superclass or face the infinite recursion consequences
            object.__setattr__(self, '_e_module_name', module_name)
            object.__setattr__(self, '_e_object', instance)

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

        def __setattr__(self, name, value):
            return setattr(self._e_object, name, value)

        def __getattr__(self, name):
            return getattr(self._e_object, name)

        def __call__(self, *args, **kwargs):
            return TimerWrapper(_e_trace(general_factory, min_duration,
                                         self._e_object, *args, **kwargs),
                                self._e_module_name)

    module.Client = Wrapper(module.Client, 'pylibmc')
