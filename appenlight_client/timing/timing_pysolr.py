from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace

ignore_set = frozenset()


def add_timing(min_duration=0.1):
    module = import_module('pysolr')
    if not module:
        return

    def general_factory(slow_call_name):
        def gather_args(solr, *args, **kwargs):
            return {'type': 'nosql', 'subtype': 'solr',
                    'statement': slow_call_name,
                    'count': True,
                    'ignore_in': ignore_set}

        return gather_args

    def gather_args_search(solr, q, *args, **kwargs):
        return {'type': 'nosql', 'subtype': 'solr', 'statement': q,
                'count': True,
                'ignore_in': ignore_set}

    def gather_args_more_like_this(solr, q, *args, **kwargs):
        return {'type': 'nosql', 'subtype': 'solr', 'statement': q,
                'count': True,
                'ignore_in': ignore_set}

    deco_func_or_method(module, 'Solr.search', time_trace,
                        gatherer=gather_args_search, min_duration=min_duration)

    deco_func_or_method(module, 'Solr.add', time_trace,
                        gatherer=general_factory('Solr.add'), min_duration=min_duration)

    deco_func_or_method(module, 'Solr.commit', time_trace,
                        gatherer=general_factory('Solr.commit'), min_duration=min_duration)

    deco_func_or_method(module, 'Solr.delete', time_trace,
                        gatherer=general_factory('Solr.delete'), min_duration=min_duration)

    deco_func_or_method(module, 'Solr.extract', time_trace,
                        gatherer=general_factory('Solr.extract'), min_duration=min_duration)

    deco_func_or_method(module, 'Solr.more_like_this', time_trace,
                        gatherer=gather_args_more_like_this, min_duration=min_duration)

    deco_func_or_method(module, 'Solr.suggest_terms', time_trace,
                        gatherer=general_factory('Solr.commit'), min_duration=min_duration)
