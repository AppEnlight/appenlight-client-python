from appenlight_client.utils import deco_func_or_method, fullyQualifiedName
from functools import wraps


def wrap_pylons_view_method_name():
    def decorator(appenlight_callable):
        @wraps(appenlight_callable)
        def view_callable_wrapper(self, environ, start_response):
            try:
                action = environ['pylons.routes_dict'].get('action', '')
                controller = fullyQualifiedName(self.__class__)
                environ['appenlight.view_name'] = "%s.%s" % (controller, action)
            except Exception:
                pass
            return appenlight_callable(self, environ, start_response)

        return view_callable_wrapper

    return decorator


def register():
    try:
        import pylons.controllers.core

        module = pylons.controllers.core
    except ImportError:
        module = None
    if not module:
        return
    deco_func_or_method(module, 'WSGIController.__call__', wrap_pylons_view_method_name)
