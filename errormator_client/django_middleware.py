import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.http import Http404
from errormator_client.exceptions import get_current_traceback
from errormator_client.timing import local_timing, get_local_storage
from errormator_client.timing import default_timer
from errormator_client.client import Client
import logging
import sys

log = logging.getLogger(__name__)


class ErrormatorMiddleware(object):
    __version__ = '0.3'

    def __init__(self):
        log.debug('setting errormator middleware')
        if not hasattr(ErrormatorMiddleware, 'client'):
            base_config = getattr(settings, 'ERRORMATOR', {})
            ErrormatorMiddleware.errormator_client = Client(config=base_config)

    def process_request(self, request):
        request.__e_processed_exception__ = False
        request.__traceback__ = None
        environ = request.environ
        environ['errormator.request_id'] = str(uuid.uuid4())
        # inject client instance reference to environ
        if 'errormator.client' not in environ:
            environ['errormator.client'] = self.errormator_client
        environ['errormator.post_vars'] = request.POST
        errormator_storage = get_local_storage(local_timing)
        # clear out thread stats on request start
        errormator_storage.clear()
        request.__start_time__ = default_timer()
        return None

    def process_exception(self, request, exception):
        if (not getattr(self, 'errormator_client') or
                not self.errormator_client.config.get('enabled')):
            return None

        request.__e_processed_exception__ = True
        environ = request.environ
        user = getattr(request, 'user', None)
        if user and user.is_authenticated():
            environ['errormator.username'] = unicode(user.pk)
        if isinstance(exception, Http404):
            http_status = 404
        else:
            http_status = 500
            request.__traceback__ = get_current_traceback(
                skip=1,
                show_hidden_frames=True,
                ignore_system_exceptions=True)

        # report 500's and 404's
        if not self.errormator_client.config['report_errors']:
            return None

        errormator_storage = get_local_storage(local_timing)
        stats, slow_calls = errormator_storage.get_thread_stats()
        self.errormator_client.py_report(
            environ,
            request.__traceback__,
            message=None,
            http_status=http_status,
            start_time=datetime.utcfromtimestamp(request.__start_time__),
            request_stats=stats)
        if request.__traceback__:
            # dereference tb object but set it to true afterwards for
            # other stuff
            del request.__traceback__
            request.__traceback__ = True

    def process_response(self, request, response):
        try:
            return response
        finally:
            if self.errormator_client.config.get('enabled'):
                end_time = default_timer()
                environ = request.environ
                user = getattr(request, 'user', None)
                if user:
                    environ['errormator.username'] = unicode(user.id)
                if (response.status_code == 404 and
                        not request.__e_processed_exception__):
                    self.process_exception(request, Http404())
                delta = timedelta(
                    seconds=(end_time - request.__start_time__))
                errormator_storage = get_local_storage(local_timing)
                errormator_storage.thread_stats[
                    'main'] = end_time - request.__start_time__
                stats, slow_calls = errormator_storage.get_thread_stats()
                # report slowness
                self.errormator_client.save_request_stats(stats)
                if self.errormator_client.config['slow_requests']:
                    # do we have slow calls ?
                    if (delta >= self.errormator_client.config[
                        'slow_request_time'] or slow_calls):
                        self.errormator_client.py_slow_report(
                            environ,
                            datetime.utcfromtimestamp(request.__start_time__),
                            datetime.utcfromtimestamp(end_time),
                            slow_calls,
                            request_stats=stats)
                        # force log fetching
                        request.__traceback__ = True

                if self.errormator_client.config['logging']:
                    records = self.errormator_client.log_handler.get_records()
                    self.errormator_client.log_handler.clear_records()
                    self.errormator_client.py_log(
                        environ, records=records,
                        r_uuid=environ['errormator.request_id'],
                        traceback=request.__traceback__)
                    # send all data we gathered immediately at the
                    # end of request
                self.errormator_client.check_if_deliver(
                    self.errormator_client.config['force_send'] or
                    environ.get('errormator.force_send'))
