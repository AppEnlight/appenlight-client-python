from __future__ import absolute_import
import logbook
import logging
import datetime

from appenlight_client.ext.logging import EXCLUDED_LOG_VARS
from appenlight_client.timing import get_local_storage
from appenlight_client.utils import asbool, parse_tag, PY3

log = logging.getLogger(__name__)


class ThreadLocalHandler(logbook.Handler):
    def __init__(self, client_config=None, *args, **kwargs):
        logbook.Handler.__init__(self, *args, **kwargs)
        self.ae_client_config = client_config

    def emit(self, record):
        appenlight_storage = get_local_storage()
        r_dict = convert_record_to_dict(record, self.ae_client_config)
        if r_dict:
            if r_dict not in appenlight_storage.logs:
                appenlight_storage.logs.append(r_dict)

    def get_records(self, thread=None):
        """
        Returns a list of records for the current thread.
        """
        appenlight_storage = get_local_storage()
        return appenlight_storage.logs

    def clear_records(self, thread=None):
        """ Clears ALL logs from AE storage """
        appenlight_storage = get_local_storage()
        appenlight_storage.logs = []


def convert_record_to_dict(record, client_config):

    if record.channel in client_config.get('log_namespace_blacklist', []):
        return None
    if not getattr(record, 'time'):
        time_string = datetime.datetime.utcnow().isoformat()
    else:
        time_string = record.time.isoformat()
    try:
        message = record.msg
        tags_list = []
        log_dict = {'log_level': record.level_name,
                    "namespace": record.channel,
                    'server': client_config.get('server_name', 'unknown'),
                    'date': time_string,
                    'request_id': None}
        if PY3:
            log_dict['message'] = '%s' % message
        else:
            msg = message.encode('utf8') if isinstance(message,
                                                       unicode) else message
            log_dict['message'] = '%s' % msg

        if client_config.get('logging_attach_exc_text'):
            pass
        # populate tags from extra
        for k, v in record.extra.iteritems():
            if k not in EXCLUDED_LOG_VARS:
                try:
                    tags_list.append(parse_tag(k, v))
                    if k == 'ae_primary_key':
                        log_dict['primary_key'] = unicode(v)
                    if k == 'ae_permanent':
                        try:
                            log_dict['permanent'] = asbool(v)
                        except Exception:
                            log_dict['permanent'] = True
                except Exception as e:
                    log.info(u'Couldn\'t convert attached tag %s' % e)
        if tags_list:
            log_dict['tags'] = tags_list
        return log_dict
    except (TypeError, UnicodeDecodeError, UnicodeEncodeError) as e:
        # handle some weird case where record.getMessage() fails
        log.warning(e)
