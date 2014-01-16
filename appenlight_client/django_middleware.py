import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.http import Http404
from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import local_timing, get_local_storage
from appenlight_client.timing import default_timer
from appenlight_client.client import Client
from appenlight_client.utils import fullyQualifiedName
import logging
import sys
import inspect

log = logging.getLogger(__name__)


class AppenlightMiddleware(object):
    __version__ = '0.3'

    def __init__(self):
        log.debug('setting appenlight middleware')
        if not hasattr(AppenlightMiddleware, 'client'):
            base_config = getattr(settings, 'APPENLIGHT') or {}
            AppenlightMiddleware.appenlight_client = Client(config=base_config)

    def process_request(self, request):
        request._errormator_create_report = False
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

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            if 'appenlight.view_name' not in request.environ:
                request.environ['appenlight.view_name'] = '%s.%s' % (fullyQualifiedName(view_func), request.method)
        except Exception,e:
            request.environ['appenlight.view_name'] = ''
        return None

    def process_exception(self, request, exception):
        if (not getattr(self, 'appenlight_client') or not self.appenlight_client.config.get('enabled')):
            return None
        environ = request.environ
        if not self.appenlight_client.config['report_errors'] or environ.get('appenlight.ignore_error'):
            return None
        user = getattr(request, 'user', None)
        end_time = default_timer()
        if user and user.is_authenticated():
            environ['appenlight.username'] = unicode(user.pk)
        if not isinstance(exception, Http404):
            http_status = 500
            request._errormator_create_report = True
            traceback = get_current_traceback(skip=1,
                                              show_hidden_frames=True,
                                              ignore_system_exceptions=True)
            appenlight_storage = get_local_storage(local_timing)
            appenlight_storage.thread_stats['main'] = end_time - request.__start_time__
            stats, slow_calls = appenlight_storage.get_thread_stats()
            self.appenlight_client.save_request_stats(stats, view_name=environ.get('appenlight.view_name',''))
            self.appenlight_client.py_report(environ,
                                             traceback,
                                             message=None,
                                             http_status=http_status,
                                             start_time=datetime.utcfromtimestamp(request.__start_time__),
                                             end_time=datetime.utcfromtimestamp(end_time),
                                             request_stats=stats,
                                             slow_calls=slow_calls)
            del traceback


    def process_response(self, request, response):
        try:
            return response
        finally:
            environ = request.environ
            enabled = self.appenlight_client.config.get('enabled')
            if enabled and not request._errormator_create_report and not environ.get('appenlight.ignore_slow'):
                end_time = default_timer()
                user = getattr(request, 'user', None)
                http_status = response.status_code
                if user and user.is_authenticated():
                    environ['appenlight.username'] = unicode(user.pk)
                if (http_status == 404 and self.appenlight_client.config['report_404']):
                    request._errormator_create_report = True
                delta = timedelta(seconds=(end_time - request.__start_time__))
                appenlight_storage = get_local_storage(local_timing)
                appenlight_storage.thread_stats['main'] = end_time - request.__start_time__
                stats, slow_calls = appenlight_storage.get_thread_stats()
                self.appenlight_client.save_request_stats(stats, view_name=environ.get('appenlight.view_name',''))
                if self.appenlight_client.config['slow_requests']:
                    if (delta >= self.appenlight_client.config['slow_request_time'] or slow_calls):
                        request._errormator_create_report = True
                if request._errormator_create_report:
                        self.appenlight_client.py_report(environ,
                                                         None,
                                                         message=None,
                                                         http_status=http_status,
                                                         start_time=datetime.utcfromtimestamp(request.__start_time__),
                                                         end_time=datetime.utcfromtimestamp(end_time),
                                                         request_stats=stats,
                                                         slow_calls=slow_calls)

                if self.appenlight_client.config['logging']:
                    records = self.appenlight_client.log_handler.get_records()
                    self.appenlight_client.log_handler.clear_records()
                    self.appenlight_client.py_log(environ,
                                                  records=records,
                                                  r_uuid=environ['appenlight.request_id'],
                                                  created_report=request._errormator_create_report)
            if self.appenlight_client.config.get('enabled'):
                self.appenlight_client.check_if_deliver(self.appenlight_client.config['force_send'] or
                                                        environ.get('appenlight.force_send'))
