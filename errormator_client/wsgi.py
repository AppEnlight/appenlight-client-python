import uuid
import datetime
from errormator_client.utils import asbool
from errormator_client.exceptions import get_current_traceback
import logging
import sys

log = logging.getLogger(__name__)

class ErrormatorWSGIWrapper(object):

    __version__ = 0.2

    def __init__(self, app, errormator_client):
        self.app = app
        self.errormator_client = errormator_client
        self.uuid = uuid.uuid4()

    def __call__(self, environ, start_response):
        """Run the application and conserve the traceback frames.
        also determine if we got 404
        """
        environ['errormator.request_id'] = str(uuid.uuid4())

        app_iter = None
        detected_data = []
        traceback = None
        start_time = datetime.datetime.utcnow()

        def detect_headers(status, headers, *k, **kw):
            detected_data[:] = status[:3], headers
            return start_response(status, headers, *k, **kw)

        # inject client instance reference to environ
        if 'errormator.client' not in environ:
            environ['errormator.client'] = self.errormator_client
        try:
            app_iter = self.app(environ, detect_headers)
            return app_iter
        except Exception as e:
            if hasattr(app_iter, 'close'):
                app_iter.close()
            #we need that here

            exc_type, exc_value, tb = sys.exc_info()
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
            # by default reraise exceptions for app/FW to handle
            if self.errormator_client.config['reraise_exceptions']:
                raise exc_type, exc_value, tb
            try:
                start_response('500 INTERNAL SERVER ERROR',
                        [('Content-Type', 'text/html; charset=utf-8')])
            except Exception as e:
                environ['wsgi.errors'].write(
                    'ErrormatorWSGIWrapper middleware catched exception in streamed'
                    ' response at a point where response headers were already'
                    ' sent.\n')
            else:
                return 'Server Error'
        finally:
            # report 500's and 404's
            if traceback and self.errormator_client.config['report_errors']:
                http_status = 500
            elif self.errormator_client.config['report_404'] and detected_data and detected_data[0] == '404':
                http_status = int(detected_data[0])
                e = '404 Not Found'
            else:
                http_status = None
            if http_status:
                url = self.errormator_client.py_report(
                                    environ,
                                    traceback,
                                    message=None,
                                    http_status=http_status)
                #leave trace of exception in logs
                log.warning(u'%s code: %s @%s' % (http_status, e, url,))

            # report slowness
            if self.errormator_client.config['slow_requests']:
                # do we have slow queries ?
                end_time = datetime.datetime.utcnow()
                delta = end_time - start_time
                records = self.errormator_client.datastore_handler.get_records()
                self.errormator_client.datastore_handler.clear_records()
                if delta >= self.errormator_client.config['slow_request_time'] or len(records) > 0:
                    self.errormator_client.py_slow_report(environ,
                                    start_time, end_time, records)
            if self.errormator_client.config['logging']:
                records = self.errormator_client.log_handler.get_records()
                self.errormator_client.log_handler.clear_records()
                self.errormator_client.py_log(environ, records=records,
                                        uuid=environ['errormator.request_id'])
