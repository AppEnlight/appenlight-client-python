import uuid
import datetime
from appenlight_client.exceptions import get_current_traceback
from appenlight_client.timing import local_timing, get_local_storage
from appenlight_client.timing import default_timer
from appenlight_client.client import PY3
import logging
import sys

log = logging.getLogger(__name__)


class AppenlightWSGIWrapper(object):
    __version__ = '0.3'

    def __init__(self, app, appenlight_client):
        self.app = app
        self.appenlight_client = appenlight_client

    def __call__(self, environ, start_response):
        """Run the application and conserve the traceback frames.
        also determine if we got 404
        """
        environ['appenlight.request_id'] = str(uuid.uuid4())
        appenlight_storage = get_local_storage(local_timing)
        # clear out thread stats on request start
        appenlight_storage.clear()
        app_iter = None
        detected_data = []
        traceback = None
        start_time = default_timer()

        def detect_headers(status, headers, *k, **kw):
            detected_data[:] = status[:3], headers
            return start_response(status, headers, *k, **kw)

        # inject client instance reference to environ
        if 'appenlight.client' not in environ:
            environ['appenlight.client'] = self.appenlight_client
            # some bw. compat stubs

            def local_report(message, include_traceback=True,
                             http_status=200):
                environ['appenlight.force_send'] = True

            def local_log(level, message):
                environ['appenlight.force_send'] = True

            environ['appenlight.report'] = local_report
            environ['appenlight.log'] = local_log

        try:
            app_iter = self.app(environ, detect_headers)
            return app_iter
        except Exception as exc:
            if hasattr(app_iter, 'close'):
                app_iter.close()
                # we need that here

            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
            # by default reraise exceptions for app/FW to handle
            if self.appenlight_client.config['reraise_exceptions']:
                raise
            try:
                start_response('500 INTERNAL SERVER ERROR',
                               [('Content-Type', 'text/html; charset=utf-8')])
            except Exception as exc:
                environ['wsgi.errors'].write(
                    'AppenlightWSGIWrapper middleware catched exception '
                    'in streamed response at a point where response headers '
                    'were already sent.\n')
            else:
                return 'Server Error'
        finally:
            # report 500's and 404's
            # report slowness
            end_time = default_timer()
            appenlight_storage.thread_stats['main'] = end_time - start_time
            stats, slow_calls = appenlight_storage.get_thread_stats()
            if 'appenlight.__traceback' in environ:
                # get traceback gathered by tween
                traceback = environ['appenlight.__traceback']
                del environ['appenlight.__traceback']
            if traceback and self.appenlight_client.config['report_errors']:
                http_status = 500
            elif (self.appenlight_client.config['report_404'] and
                      detected_data and detected_data[0] == '404'):
                http_status = int(detected_data[0])
            else:
                http_status = None
            if http_status:
                self.appenlight_client.py_report(
                    environ, traceback,
                    message=None,
                    http_status=http_status,
                    start_time=datetime.datetime.utcfromtimestamp(
                        start_time),
                    request_stats=stats)
                # dereference
                del traceback
                traceback = True
            delta = datetime.timedelta(seconds=(end_time - start_time))
            self.appenlight_client.save_request_stats(stats)
            if self.appenlight_client.config['slow_requests']:
                # do we have slow calls ?
                if (delta >= self.appenlight_client.config['slow_request_time']
                    or slow_calls):
                    self.appenlight_client.py_slow_report(
                        environ,
                        datetime.datetime.utcfromtimestamp(start_time),
                        datetime.datetime.utcfromtimestamp(end_time),
                        slow_calls,
                        request_stats=stats)
                    # force log fetching
                    traceback = True
            if self.appenlight_client.config['logging']:
                records = self.appenlight_client.log_handler.get_records()
                self.appenlight_client.log_handler.clear_records()
                self.appenlight_client.py_log(
                    environ,
                    records=records,
                    r_uuid=environ[
                        'appenlight.request_id'],
                    traceback=traceback)
                # send all data we gathered immediately at the end of request
            self.appenlight_client.check_if_deliver(
                self.appenlight_client.config['force_send'] or
                environ.get('appenlight.force_send'))
