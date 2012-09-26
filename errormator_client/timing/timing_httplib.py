from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

def add_timing(min_duration=3):
    module = import_module('httplib')
    if not module:
        return
    
    def gather_args_host(c):
        return {'type':'remote_call',
                'statement':'httplib.HTTPConnection.connect',
                'parameters':c.host}

    def gather_args_sslhost(c):
        return {'type':'remote_call',
                'statement':'httplib.HTTPSConnection.connect',
                'parameters':c.host}
    
    deco_func_or_method(module, 'HTTPConnection.connect', time_trace,
                          gather_args_host, min_duration)
    
    deco_func_or_method(module, 'HTTPSConnection.connect', time_trace,
                          gather_args_sslhost, min_duration)
