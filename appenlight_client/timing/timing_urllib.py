from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset(['remote', 'nosql'])


def add_timing(min_duration=3):
    module = import_module('urllib')
    if not module:
        return

    def gather_args_open(opener, url, *args, **kwargs):
        return {'type': 'remote', 'statement': 'urllib.URLopener.open',
                'parameters': url,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module, 'URLopener.open', time_trace,
                        gatherer=gather_args_open, min_duration=min_duration)

    def gather_args_urlretrieve(url, *args, **kwargs):
        return {'type': 'remote', 'statement': 'urllib.urlretrieve',
                'parameters': url,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module, 'urlretrieve', time_trace,
                        gatherer=gather_args_urlretrieve, min_duration=min_duration)
