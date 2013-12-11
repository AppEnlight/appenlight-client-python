from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import get_local_storage, local_timing
from appenlight_client.utils import fullyQualifiedName
from pyramid.tweens import EXCVIEW
from pyramid.static import static_view
import pyramid
import logging

from functools import wraps

log = logging.getLogger(__name__)

def pyramid_view_name(appenlight_callable):
    @wraps(appenlight_callable)
    def adapter_lookup(*args, **kwargs):
        view_callable = appenlight_callable(*args, **kwargs)
        appenlight_storage = get_local_storage(local_timing)
        if not view_callable:
            return view_callable
        try:
            view_name = fullyQualifiedName(view_callable)
        except Exception, e:
            view_name = ''
        appenlight_storage.view_name = view_name
        return view_callable
    return adapter_lookup

def appenlight_tween_factory(handler, registry):
    blacklist = (pyramid.httpexceptions.WSGIHTTPException,)

    def error_tween(request):
        try:
            if not hasattr(request.registry.adapters.lookup, '_appenlight_traced'):
                request.registry.adapters.lookup = pyramid_view_name(request.registry.adapters.lookup)
                request.registry.adapters.lookup._appenlight_traced = True
        except Exception as e:
            raise
            log.error("Couldn't decorate pyramid adapter")
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
