from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace


def add_timing(min_duration=3):
    module = import_module('urllib3')
    if not module:
        return

    def gather_args_url(r, m, url, *args, **kwargs):
        return {'type':'remote',
                'statement':'urllib3.request.RequestMethods.request_encode_url',
                'parameters':url}

    deco_func_or_method(module.request, 'RequestMethods.request_encode_url',
                        time_trace, gather_args_url, min_duration)


    def gather_args_body(r, m, url, *args, **kwargs):
        return {'type':'remote',
                'statement':'urllib3.request.RequestMethods.request_encode_body',
                'parameters':url}

    deco_func_or_method(module.request, 'RequestMethods.request_encode_body',
                        time_trace, gather_args_body, min_duration)
