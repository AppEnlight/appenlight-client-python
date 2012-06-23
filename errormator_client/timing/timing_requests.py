from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

def add_timing(min_duration=0.5):
    module = import_module('requests')

    def gather_args_url(method, url, *args, **kwargs):           
        return {'type':'requests.request', 'parameters':url}
    
    deco_func_or_method(module, 'api.request', time_trace,
                          gather_args_url, min_duration)
