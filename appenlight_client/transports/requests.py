from __future__ import absolute_import
import logging
import requests
import urlparse
import threading
from appenlight_client.ext_json import json
from appenlight_client import __protocol_version__, __version__


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
        update_options['timeout'] = float(update_options.get('timeout', 5))
        self.transport_config.update(update_options)

    def feed(self, *args, **kwargs):
        if self.transport_config['threaded']:
            submit_data_t = threading.Thread(target=self.submit,
                                             args=args, kwargs=kwargs)
            submit_data_t.start()
        else:
            self.submit(*args, **kwargs)
        return True

    def submit(self, *args, **kwargs):
        self.send(kwargs.get('reports') or [], 'reports')
        self.send(kwargs.get('logs') or [], 'logs')
        self.send(kwargs.get('metrics') or [], 'metrics')

    def send(self, to_send_items, endpoint):
        if to_send_items:
            try:
                return self.remote_call(to_send_items,
                                        self.client_config['endpoints'][
                                            endpoint])
            except KeyboardInterrupt as exc:
                raise KeyboardInterrupt()
            except Exception as exc:
                log.warning('%s: connection issue: %s' % (endpoint, exc))
        return False

    def remote_call(self, data, endpoint):
        if not self.client_config['api_key']:
            log.warning('no api key set - dropping payload')
            return False
        server_url = '%s%s' % (self.transport_config['url'], endpoint)
        headers = {'content-type': 'application/json',
                   'x-appenlight-api-key': self.client_config['api_key'],
                   'User-Agent': 'appenlight-python/%s' % __version__}
        log.info('sending out %s entries to %s' % (len(data), endpoint,))
        try:
            result = requests.post(server_url,
                                   data=json.dumps(data).encode('utf8'),
                                   headers=headers,
                                   timeout=self.transport_config['timeout'],
                                   params={
                                       'protocol_version': __protocol_version__},
                                   verify=True)
        except requests.exceptions.RequestException as e:
            message = 'APPENLIGHT: problem: %s' % e
            log.error(message)
            return False
        if result.status_code != 200:
            message = 'APPENLIGHT: response code: %s' % result.status_code
            log.error(message)
            return False
        return True
