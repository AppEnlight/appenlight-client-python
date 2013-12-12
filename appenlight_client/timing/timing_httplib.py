from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset(['remote', 'nosql'])


def add_timing(min_duration=3):
    module = import_module('httplib')
    if not module:
        return

    def gather_args_host(c):
        return {'type': 'remote',
                'statement': 'httplib.HTTPConnection.connect',
                'parameters': c.host,
                'count': True,
                'ignore_in': ignore_set}

    def gather_args_sslhost(c):
        return {'type': 'remote',
                'statement': 'httplib.HTTPSConnection.connect',
                'parameters': c.host,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module, 'HTTPConnection.connect', time_trace,
                        gatherer=gather_args_host, min_duration=min_duration)

    deco_func_or_method(module, 'HTTPSConnection.connect', time_trace,
                        gatherer=gather_args_sslhost, min_duration=min_duration)
