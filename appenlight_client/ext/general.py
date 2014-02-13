from appenlight_client.exceptions import get_current_traceback, Traceback
from appenlight_client.timing import local_timing, get_local_storage
import datetime
import logging
import uuid

log = logging.getLogger(__name__)


def gather_data(client, environ=None, gather_exception=True,
                gather_slowness=True, gather_logs=True,
                clear_storage=True, exc_info=None,
                start_time=None, end_time=None):
    """ exc_info is supposed to be (exc_type, exc_value, tb) - what sys.exc_info() returns """
    if client.config['enabled'] == False:
        return None
    if environ is None:
        environ = {}
    if not environ.get('appenlight.request_id'):
        environ['appenlight.request_id'] = str(uuid.uuid4())
    http_status = 200
    traceback = None
    if gather_exception and not exc_info:
        traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                          ignore_system_exceptions=True)
        if traceback:
            http_status = 500
    elif exc_info:
        traceback = Traceback(*exc_info)
        http_status = 500
    appenlight_storage = get_local_storage(local_timing)
    stats, slow_calls = appenlight_storage.get_thread_stats()
    if traceback is not None or (slow_calls and gather_slowness):
        client.py_report(environ, traceback, http_status=http_status, request_stats=stats, slow_calls=slow_calls)
    # dereference
    del traceback
    now = datetime.datetime.utcnow()
    if client.config['logging']:
        if gather_logs:
            records = client.log_handler.get_records()
            client.log_handler.clear_records()
            client.py_log(environ, records=records, r_uuid=environ['appenlight.request_id'])
    if clear_storage:
        appenlight_storage.clear()
    client.check_if_deliver(client.config['force_send'] or
                            environ.get('appenlight.force_send'))
