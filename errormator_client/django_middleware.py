import uuid
import datetime
from django.conf import settings
from django.http import Http404
from errormator_client.exceptions import get_current_traceback
from errormator_client.client import Client
import logging
import sys

log = logging.getLogger(__name__)


class ErrormatorMiddleware(object):

    __version__ = '0.2'

    def __init__(self):
        log.debug('setting errormator middleware')
        if not hasattr(ErrormatorMiddleware, 'client'):
            base_config = getattr(settings, 'ERRORMATOR', {})
            ErrormatorMiddleware.errormator_client = Client(config=base_config)
        self.uuid = uuid.uuid4()

    def process_request(self, request):
        self.uuid = uuid.uuid4()
        self.processed_exception = False
        environ = request.environ
        environ['errormator.request_id'] = str(uuid.uuid4())
        # inject client instance reference to environ
        if 'errormator.client' not in environ:
            environ['errormator.client'] = self.errormator_client
        self.start_time = datetime.datetime.utcnow()
        return None

    def process_exception(self, request, exception):
        self.processed_exception = True
        environ = request.environ
        if isinstance(exception, Http404):
            http_status = 404
            traceback = None
        else:
            http_status = 500
            exc_type, exc_value, tb = sys.exc_info()
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)

        # report 500's and 404's
        if not self.errormator_client.config['report_errors']:
            return None

        self.errormator_client.py_report(environ, traceback,
                                         message=None,
                                         http_status=http_status,
                                         start_time=self.start_time)

    def process_response(self, request, response):
        environ = request.environ

        if response.status_code == 404 and not self.processed_exception:
            self.process_exception(request, Http404())

        # report slowness
        if self.errormator_client.config['slow_requests']:
            # do we have slow queries ?
            end_time = datetime.datetime.utcnow()
            delta = end_time - self.start_time
            records = self.errormator_client.datastore_handler.get_records()
            self.errormator_client.datastore_handler.clear_records()
            if (delta >= self.errormator_client.config['slow_request_time']
                or records):
                self.errormator_client.py_slow_report(environ,
                                self.start_time, end_time, records)

        if self.errormator_client.config['logging']:
            records = self.errormator_client.log_handler.get_records()
            self.errormator_client.log_handler.clear_records()
            self.errormator_client.py_log(environ, records=records,
                                r_uuid=environ['errormator.request_id'])
        # send all data we gathered immediately at the end of request
        self.errormator_client.check_if_deliver(
                self.errormator_client.config['force_send'] or
                environ.get('errormator.force_send'))
        return response