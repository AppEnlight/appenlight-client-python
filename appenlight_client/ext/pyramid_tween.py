from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import get_local_storage, local_timing
from appenlight_client.utils import fullyQualifiedName, deco_func_or_method
from pyramid.tweens import EXCVIEW
from pyramid.static import static_view
import pyramid.config
import pyramid
import logging

from functools import wraps

log = logging.getLogger(__name__)


def pyramid_view_name(appenlight_callable):
    @wraps(appenlight_callable)
    def view_callable_wrapper(*args, **kwargs):
        appenlight_storage = get_local_storage(local_timing)
        try:
            view_name = fullyQualifiedName(appenlight_callable)
        except Exception, e:
            view_name = ''
        appenlight_storage.view_name = view_name
        return appenlight_callable(*args, **kwargs)

    return view_callable_wrapper


def wrap_view_config(appenlight_callable):
    @wraps(appenlight_callable)
    def wrapper(*args, **kwargs):
        if 'view' in kwargs:
            try:
                kwargs['view'] = pyramid_view_name(kwargs['view'])
            except Exception, e:
                pass
        return appenlight_callable(*args, **kwargs)

    return wrapper


def appenlight_tween_factory(handler, registry):
    blacklist = (pyramid.httpexceptions.WSGIHTTPException,)

    def error_tween(request):
        try:
            response = handler(request)
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
