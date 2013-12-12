from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset(['remote', 'nosql'])


def add_timing(min_duration=3):
    module = import_module('urllib2')
    if not module:
        return

    def gather_args_open(opener, url, *args, **kwargs):
        if not isinstance(url, basestring):
            g_url = url.get_full_url()
        else:
            g_url = url

        return {'type': 'remote', 'statement': 'urllib2.OpenerDirector.open',
                'parameters': g_url,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module, 'OpenerDirector.open', time_trace,
                        gatherer=gather_args_open, min_duration=min_duration)
