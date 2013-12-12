from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import get_local_storage, local_timing
from appenlight_client.utils import fullyQualifiedName, deco_func_or_method
from pyramid.tweens import EXCVIEW
from pyramid.static import static_view
import pkg_resources
import pyramid.config
import pyramid
import logging
import inspect

from functools import wraps

log = logging.getLogger(__name__)

# stolen from pyramid 1.4
def combine(*decorators):
    def decorated(view_callable):
        # reversed() is allows a more natural ordering in the api
        for decorator in reversed(decorators):
            view_callable = decorator(view_callable)
        return view_callable

    return decorated


# feature sniffing
pyramid_version_str = pkg_resources.get_distribution('pyramid').version
pyramid_version = float(pyramid_version_str[:3])
test_ver = None
can_append_decorator = False
for vchar in ['a', 'b']:
    if vchar in pyramid_version_str:
        test_ver = pyramid_version_str[pyramid_version_str.index(vchar):]
if pyramid_version > 1.4 or pyramid_version == 1.4 and test_ver not in ['a0', 'a1', 'a2', 'a3']:
    can_append_decorator = True


def wrap_pyramid_view_method_name(appenlight_callable):
    """This add missing methods to name"""

    @wraps(appenlight_callable)
    def view_callable_wrapper(*args, **kwargs):
        appenlight_storage = get_local_storage(local_timing)
        if hasattr(appenlight_storage, 'view_name'):
            try:
                appenlight_storage.view_name = '%s.%s' % (appenlight_storage.view_name,
                                                          appenlight_callable.__name__)
            except Exception, e:
                pass
        return appenlight_callable(*args, **kwargs)

    return view_callable_wrapper


def wrap_pyramid_view_name(appenlight_callable):
    @wraps(appenlight_callable)
    def view_callable_wrapper(context, request):
        appenlight_storage = get_local_storage(local_timing)
        view_name = ''
        try:
            original_view = getattr(appenlight_callable, '__original_view__')
            if original_view:
                view_name = fullyQualifiedName(appenlight_callable)
                if not hasattr(original_view, '_appenlight_name') and inspect.isclass(original_view):
                    original_view._appenlight_name = view_name
                    for k, v in original_view.__dict__.items():
                        if not k.startswith('_'):
                            setattr(original_view, k, wrap_pyramid_view_method_name(v))
        except Exception, e:
            raise
        if 'pyramid/static' in view_name:
            #normalize static views
            view_name = 'pyramid/static'
        appenlight_storage.view_name = view_name
        return appenlight_callable(context, request)

    return view_callable_wrapper


def wrap_view_config(appenlight_callable):
    @wraps(appenlight_callable)
    def wrapper(*args, **kwargs):
        if not 'decorator' in kwargs:
            if can_append_decorator:
                kwargs['decorator'] = wrap_pyramid_view_name
        else:
            if can_append_decorator:
                kwargs['decorator'].append(wrap_pyramid_view_name)
        return appenlight_callable(*args, **kwargs)

    return wrapper


def appenlight_tween_factory(handler, registry):
    blacklist = (pyramid.httpexceptions.WSGIHTTPException,)

    def error_tween(request):
        try:
            response = handler(request)
            appenlight_storage = get_local_storage(local_timing)
        except blacklist as e:
            raise
        except:
            if 'appenlight.client' in request.environ:
                # pass the traceback object to middleware
                request.environ[
                    'appenlight.__traceback'] = get_current_traceback(
                    skip=1,
                    show_hidden_frames=True,
                    ignore_system_exceptions=True)
            raise
        return response

    return error_tween


def includeme(config):
    config.add_tween(
        'appenlight_client.ext.pyramid_tween.appenlight_tween_factory',
        under=EXCVIEW)
    setattr(pyramid.config.Configurator, 'add_view',
            wrap_view_config(pyramid.config.Configurator.add_view)
    )
