from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

def add_timing(min_duration=3):
    module = import_module('urllib')
    if not module:
        return
    
    def gather_args_open(opener, url, *args, **kwargs):
        return {'type':'remote_call',
                'statement':'urllib.URLopener.open',
                'parameters':url}
    
    deco_func_or_method(module, 'URLopener.open', time_trace,
                          gather_args_open, min_duration)
    
    
    def gather_args_urlretrieve(url, *args, **kwargs):
        return {'type':'remote_call',
                'statement':'urllib.urlretrieve', 'parameters':url}
    
    deco_func_or_method(module, 'urlretrieve', time_trace,
                          gather_args_urlretrieve, min_duration
                          )
