import logging
import sys
import urlparse
import threading
from appenlight_client.ext_json import json
from appenlight_client import __protocol_version__, __version__

# are we running python 3.x ?
PY3 = sys.version_info[0] == 3

if PY3:
    import urllib
else:
    import urllib
    import urllib2

log = logging.getLogger(__name__)


class HTTPTransport(object):
    def __init__(self, config_string, client_config):
        self.client_config = client_config
        self.transport_config = {'endpoints': {"reports": '/api/reports',
                                               "logs": '/api/logs',
                                               "metrics": '/api/metrics'}
        }
        parsed_url = urlparse.urlsplit(config_string)

        self.transport_config['url'] = parsed_url.geturl().split('?')[0]
        update_options = dict(urlparse.parse_qsl(parsed_url.query))
        update_options['threaded'] = int(update_options.get('threaded', 1))
        update_options['timeout'] = int(update_options.get('timeout', 5))
        self.transport_config.update(update_options)

    def feed(self, *args, **kwargs):
        if self.transport_config['threaded']:
            submit_data_t = threading.Thread(target=self.submit,
                                        args=args,kwargs=kwargs)
            submit_data_t.start()
        else:
            self.submit_data(*args, **kwargs)
        return True

    def submit(self, *args, **kwargs):
        self.send(kwargs.get('reports') or [], 'reports')
        self.send(kwargs.get('logs') or [], 'logs')
        self.send(kwargs.get('metrics') or [], 'metrics')

    def send(self, to_send_items, endpoint):
        if to_send_items:
            try:
                return self.remote_call(to_send_items,
                                 self.client_config['endpoints'][endpoint])
            except KeyboardInterrupt as exc:
                raise KeyboardInterrupt()
            except Exception as exc:
                log.warning('%s: connection issue: %s' % (endpoint, exc))
        return False

    def remote_call(self, data, endpoint):
        if not self.client_config['api_key']:
            log.warning('no api key set - dropping payload')
            return False
        GET_vars = urllib.urlencode({
            'protocol_version': __protocol_version__})
        server_url = '%s%s?%s' % (self.transport_config['url'], endpoint,
                                  GET_vars,)
        headers = {'content-type': 'application/json',
                   'x-appenlight-api-key': self.client_config['api_key'],
                   'User-Agent':'appenlight-python/%s' % __version__}
        log.info('sending out %s entries to %s' % (len(data), endpoint,))
        try:
            req = urllib2.Request(server_url,
                                  json.dumps(data).encode('utf8'),
                                  headers=headers)
        except IOError as e:
            message = 'APPENLIGHT: problem: %s' % e
            log.error(message)
            return False
        try:
            conn = urllib2.urlopen(req,
                                   timeout=self.transport_config['timeout'])
            conn.close()
            return True
        except TypeError as exc:
            conn = urllib2.urlopen(req)
            conn.close()
            return True
        if conn.getcode() != 200:
            message = 'APPENLIGHT: response code: %s' % conn.getcode()
            log.error(message)
        return False