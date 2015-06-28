from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset()


def add_timing(min_duration=0.15):
    module = import_module('mako')
    if not module:
        return

    from mako import template

    def gather_template(self, *args, **kwargs):
        try:
            tmpl_name = str(self.filename or self.module_id)
        except Exception:
            tmpl_name = ''
        return {'type': 'tmpl',
                'subtype': 'mako',
                'statement': 'render',
                'parameters': tmpl_name,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(template, 'Template.render', time_trace,
                        gatherer=gather_template, min_duration=min_duration, is_template=True)
    deco_func_or_method(template, 'Template.render_unicode', time_trace,
                        gatherer=gather_template, min_duration=min_duration, is_template=True)
    deco_func_or_method(template, 'Template.render_context', time_trace,
                        gatherer=gather_template, min_duration=min_duration, is_template=True)
