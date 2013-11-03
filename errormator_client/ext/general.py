from errormator_client.exceptions import get_current_traceback, Traceback
from errormator_client.timing import local_timing, get_local_storage
import datetime
import logging
import uuid

log = logging.getLogger(__name__)


def gather_data(client, environ, gather_exception=True,
                gather_slowness=True, gather_logs=True,
                clear_storage=True, exc_info=None, spawn_thread=True):
    if client.config['enabled'] == False:
        return None
    if not environ.get('wsgi.url_scheme'):
        environ['wsgi.url_scheme'] = ''
    if not environ.get('HTTP_HOST'):
        environ['HTTP_HOST'] = 'localhost'
    if not environ.get('errormator.request_id'):
        environ['errormator.request_id'] = str(uuid.uuid4())
    if gather_exception and not exc_info:
        traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                          ignore_system_exceptions=True)
    elif exc_info:
        traceback = Traceback(*exc_info)
    else:
        traceback = None
    errormator_storage = get_local_storage(local_timing)
    stats, slow_calls = errormator_storage.get_thread_stats()
    if traceback:
        client.py_report(environ, traceback, http_status=500,
                         request_stats=stats)
        # dereference
        del traceback
        traceback = True
        # report slowness
    now = datetime.datetime.utcnow()
    if clear_storage:
        errormator_storage.clear()
    if client.config['slow_requests'] and gather_slowness:
        # do we have slow calls ?
        if (slow_calls):
            client.py_slow_report(environ, now, now, slow_calls,
                                  request_stats=stats)
            # force log fetching
            traceback = True

    if client.config['logging'] and gather_logs:
        records = client.log_handler.get_records()
        client.log_handler.clear_records()
        client.py_log(environ, records=records, traceback=traceback,
                      r_uuid=environ['errormator.request_id'])
        # send all data we gathered immediately at the end of request
    client.check_if_deliver(client.config['force_send'] or
                            environ.get('errormator.force_send'),
                            spawn_thread=spawn_thread)
