from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset()


def add_timing(min_duration=0.15):
    module = import_module('django')
    if not module:
        return

    from django import template

    def gather_template(self, *args, **kwargs):
        try:
            tmpl_name = str(self.name)
        except Exception:
            tmpl_name = ''
        return {'type': 'tmpl',
                'subtype': 'django',
                'statement': 'render',
                'count': True,
                'parameters': tmpl_name,
                'ignore_in': ignore_set}

    if hasattr(template.Template, 'render'):
        deco_func_or_method(template, 'Template.render', time_trace,
                            gatherer=gather_template, min_duration=min_duration, is_template=True)
    elif hasattr(template.Template, '_render'):
        deco_func_or_method(template, 'Template._render', time_trace,
                            gatherer=gather_template, min_duration=min_duration, is_template=True)
