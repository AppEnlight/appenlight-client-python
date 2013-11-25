from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import get_local_storage, local_timing
from pyramid.tweens import EXCVIEW
import pyramid
import logging

log = logging.getLogger(__name__)


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
