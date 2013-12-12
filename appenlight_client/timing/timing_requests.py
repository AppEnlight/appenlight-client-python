from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset(['remote', 'nosql'])


def add_timing(min_duration=3):
    module = import_module('requests')
    if not module:
        return

    def gather_args_url(method, url, *args, **kwargs):
        return {'type': 'remote', 'statement': 'requests.request',
                'parameters': url,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module, 'api.request', time_trace,
                        gatherer=gather_args_url, min_duration=min_duration)
