from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace, import_from_module, _e_trace

def add_timing(min_duration=0.15):
    module = import_module('jinja2')
    if not module:
        return
    
    from jinja2 import environment
   
    def gather_template(template, *args, **kwargs):
        return {'type':'template',
                'statement':'render_jinja2',
                'parameters':''}
        
    if hasattr(environment.Template, '_e_attached_wrapper'):
        return
    deco_func_or_method(environment, 'Template.render', time_trace,
                          gather_template, min_duration, is_template=True)
    
    environment.Environment.template_class = environment.Template
    module.Template = environment.Template
