import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.http import Http404
from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import local_timing, get_local_storage
from appenlight_client.timing import default_timer
from appenlight_client.client import Client
import logging
import sys

log = logging.getLogger(__name__)


class AppenlightMiddleware(object):
    __version__ = '0.3'

    def __init__(self):
        log.debug('setting appenlight middleware')
        if not hasattr(AppenlightMiddleware, 'client'):
            base_config = getattr(settings, 'APPENLIGHT', {})
            AppenlightMiddleware.appenlight_client = Client(config=base_config)

    def process_request(self, request):
        request.__e_processed_exception__ = False
        request.__traceback__ = None
        environ = request.environ
        environ['appenlight.request_id'] = str(uuid.uuid4())
        # inject client instance reference to environ
        if 'appenlight.client' not in environ:
            environ['appenlight.client'] = self.appenlight_client
        environ['appenlight.post_vars'] = request.POST
        appenlight_storage = get_local_storage(local_timing)
        # clear out thread stats on request start
        appenlight_storage.clear()
        request.__start_time__ = default_timer()
        return None

    def process_exception(self, request, exception):
        if (not getattr(self, 'appenlight_client') or
                not self.appenlight_client.config.get('enabled')):
            return None

        request.__e_processed_exception__ = True
        environ = request.environ
        user = getattr(request, 'user', None)
        if user and user.is_authenticated():
            environ['appenlight.username'] = unicode(user.pk)
        if isinstance(exception, Http404):
            http_status = 404
        else:
            http_status = 500
            request.__traceback__ = get_current_traceback(
                skip=1,
                show_hidden_frames=True,
                ignore_system_exceptions=True)

        # report 500's and 404's
        if not self.appenlight_client.config['report_errors']:
            return None

        appenlight_storage = get_local_storage(local_timing)
        stats, slow_calls = appenlight_storage.get_thread_stats()
        self.appenlight_client.py_report(
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
            if self.appenlight_client.config.get('enabled'):
                end_time = default_timer()
                environ = request.environ
                user = getattr(request, 'user', None)
                if user:
                    environ['appenlight.username'] = unicode(user.id)
                if (response.status_code == 404 and
                        not request.__e_processed_exception__):
                    self.process_exception(request, Http404())
                delta = timedelta(
                    seconds=(end_time - request.__start_time__))
                appenlight_storage = get_local_storage(local_timing)
                appenlight_storage.thread_stats[
                    'main'] = end_time - request.__start_time__
                stats, slow_calls = appenlight_storage.get_thread_stats()
                # report slowness
                self.appenlight_client.save_request_stats(stats)
                if self.appenlight_client.config['slow_requests']:
                    # do we have slow calls ?
                    if (delta >= self.appenlight_client.config[
                        'slow_request_time'] or slow_calls):
                        self.appenlight_client.py_slow_report(
                            environ,
                            datetime.utcfromtimestamp(request.__start_time__),
                            datetime.utcfromtimestamp(end_time),
                            slow_calls,
                            request_stats=stats)
                        # force log fetching
                        request.__traceback__ = True

                if self.appenlight_client.config['logging']:
                    records = self.appenlight_client.log_handler.get_records()
                    self.appenlight_client.log_handler.clear_records()
                    self.appenlight_client.py_log(
                        environ, records=records,
                        r_uuid=environ['appenlight.request_id'],
                        traceback=request.__traceback__)
                    # send all data we gathered immediately at the
                    # end of request
                self.appenlight_client.check_if_deliver(
                    self.appenlight_client.config['force_send'] or
                    environ.get('appenlight.force_send'))
