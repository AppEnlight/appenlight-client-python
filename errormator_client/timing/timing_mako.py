from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace, import_from_module, _e_trace

def add_timing(min_duration=0.05):
    module = import_module('mako')
    if not module:
        return
    
    from mako import template
    
    class Wrapper(object):
        
        _e_attached_wrapper = True
        
        def __init__(self, class_obj):
            # assign to superclass or face the infinite recursion consequences
            object.__setattr__(self, '_e_object', class_obj)
        
        def __setattr__(self, name, value):
            return setattr(self._e_object, name, value)
        
        def __getattr__(self, name):
            return getattr(self._e_object, name)
        
        def __call__(self, *args, **kwargs):
            tmpl = kwargs.get('filename', 'textual')
            def gather_args_render(*args, **kwargs):
                return {'type':'template',
                        'statement':'mako_render',
                        'parameters':tmpl}
           
            deco_func_or_method(template, 'Template.render', time_trace,
                          gather_args_render, min_duration)
            deco_func_or_method(template, 'Template.render_unicode', time_trace,
                          gather_args_render, min_duration)
            deco_func_or_method(template, 'Template.render_context', time_trace,
                          gather_args_render, min_duration)  
            return self._e_object(*args, **kwargs)
    if hasattr(template.Template, '_e_attached_wrapper'):
        return        
    template.Template = Wrapper(template.Template)
