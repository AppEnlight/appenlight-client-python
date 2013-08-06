from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

import logging

ignore_set = frozenset()

to_decorate = ['add', 'append', 'cas', 'decr', 'delete', 'delete_multi',
               'get', 'gets', 'get_multi', 'incr', 'prepend', 'replace',
               'set', 'set_multi']

def add_timing(min_duration=0.1):
    module = import_module('memcache')
    if not module:
        return

    def general_factory(slow_call_name):
        def gather_args(self, *args, **kwargs):
            return {'type': 'nosql', 'subtype': 'memcache-py',
                    'count': True,
                    'statement': slow_call_name,
                    'ignore_in': ignore_set}

        return gather_args

    for m in to_decorate:
        deco_func_or_method(module, 'Client.%s' % m, time_trace,
                        general_factory('%s' % m), min_duration)