from errormator_client.exceptions import get_current_traceback
from errormator_client.timing import get_local_storage, local_timing
from pyramid.tweens import EXCVIEW
import pyramid
import logging

log = logging.getLogger(__name__)


def errormator_tween_factory(handler, registry):
    blacklist = (pyramid.httpexceptions.WSGIHTTPException,)

    def error_tween(request):
        try:
            response = handler(request)
        except blacklist as e:
            raise
        except:
            if 'errormator.client' in request.environ:
                # pass the traceback object to middleware
                request.environ[
                    'errormator.__traceback'] = get_current_traceback(
                    skip=1,
                    show_hidden_frames=True,
                    ignore_system_exceptions=True)
            raise
        return response

    return error_tween


def includeme(config):
    config.add_tween(
        'errormator_client.ext.pyramid_tween.errormator_tween_factory',
        under=EXCVIEW)
