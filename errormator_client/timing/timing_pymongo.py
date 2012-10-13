from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

import logging

to_decorate = ['count', 'create_index', 'distinct', 'drop', 'drop_index',
               'drop_indexes', 'ensure_index', 'find', 'find_one',
               'find_and_modify' 'group', 'index_information',
               'inline_map_reduce', 'insert', 'map_reduce', 'options',
               'reindex', 'remove', 'rename', 'save', 'update']


def add_timing(min_duration=0.3):
    module = import_module('pymongo')
    if not module:
        return
    logging.warning('mongodb timing is currently experimental')

    from pymongo.collection import Collection

    def general_factory(slow_call_name):
        def gather_args(self, *args, **kwargs):
            return {'type': 'nosql', 'subtype': 'mongo',
                    'statement': slow_call_name}
        return gather_args

    for m in to_decorate:
        deco_func_or_method(module.collection, 'Collection.%s' % m, time_trace,
                    general_factory('%s' % m), min_duration)
