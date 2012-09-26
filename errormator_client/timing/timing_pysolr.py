from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

import pysolr

def add_timing(min_duration=0.3):
    module = import_module('pysolr')
    if not module:
        return
    
    def general_factory(slow_call_name):
        def gather_args(solr, *args, **kwargs):
            return {'type':'solr', 'statement':slow_call_name}
        return gather_args
    
    def gather_args_search(solr, q, *args, **kwargs):
        return {'type':'solr', 'statement':q}

    def gather_args_more_like_this(solr, q, *args, **kwargs):
        return {'type':'solr', 'statement':q}
    
    deco_func_or_method(module, 'Solr.search', time_trace,
                          gather_args_search, min_duration)
    
    deco_func_or_method(module, 'Solr.add', time_trace,
                          general_factory('Solr.add'), min_duration)

    deco_func_or_method(module, 'Solr.commit', time_trace,
                          general_factory('Solr.commit'), min_duration)

    deco_func_or_method(module, 'Solr.delete', time_trace,
                          general_factory('Solr.delete'), min_duration)
    
    deco_func_or_method(module, 'Solr.extract', time_trace,
                          general_factory('Solr.extract'), min_duration)

    deco_func_or_method(module, 'Solr.more_like_this', time_trace,
                        gather_args_more_like_this, min_duration)
  
    deco_func_or_method(module, 'Solr.suggest_terms', time_trace,
                        general_factory('Solr.commit'), min_duration)
  
  
