from errormator_client.exceptions import get_current_traceback
from errormator_client.timing import local_timing
import datetime
import logging
import uuid

log = logging.getLogger(__name__)

def gather_data(client, environ, gather_slowness=True, gather_logs=True):
    if not environ.get('wsgi.url_scheme'):
        environ['wsgi.url_scheme'] = ''
    if not environ.get('HTTP_HOST'):
        environ['HTTP_HOST'] = 'localhost'
    if not environ.get('errormator.request_id'): 
        environ['errormator.request_id'] = str(uuid.uuid4())
    traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
    client.py_report(environ, traceback, http_status=500)
    # report slowness
    now = datetime.datetime.utcnow()
    if client.config['slow_requests'] and gather_slowness:
        # do we have slow calls ?
        records = []
        if hasattr(local_timing, '_errormator'):
            for record in local_timing._errormator.get_slow_calls():
                records.append(record)
        if (records):
            client.py_slow_report(environ, now, now, records)
            # force log fetching
            traceback = True
            
    if client.config['logging'] and gather_logs:
        records = client.log_handler.get_records()
        client.log_handler.clear_records()
        client.py_log(environ, records=records, traceback=traceback,
                      r_uuid=environ['errormator.request_id'])
    # send all data we gathered immediately at the end of request
    client.check_if_deliver(client.config['force_send'] or
                             environ.get('errormator.force_send'))
