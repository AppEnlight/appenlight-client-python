from errormator_client.utils import import_module, deco_func_or_method
from errormator_client.timing import time_trace

ignore_set = frozenset()


def add_timing(min_duration=0.15):
    module = import_module('chameleon')
    if not module:
        return

    def gather_template(template, *args, **kwargs):
        return {'type': 'tmpl',
                'subtype': 'chameleon',
                'statement': 'render',
                'parameters': '',
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module.template, 'Template.render', time_trace,
                        gather_template, min_duration, is_template=True)
