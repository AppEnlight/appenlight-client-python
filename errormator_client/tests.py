import unittest
import datetime

from errormator_client import client

TEST_ENVIRON = {
                'bfg.routes.matchdict': {'action': u'error'},
'HTTP_COOKIE': 'country=US; http_referer="http://localhost:5000/"; __utma=111872281.364819761.1329226608.1329827682.1329832005.16; __utmz=111872281.1329226608.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); _chartbeat2=y7h8jjwkw7rs69z7.1329226611838; test_group_id=5; sessionId=ec3ae1fce62f51178a88d5adef2851e5;',
'SERVER_SOFTWARE': 'waitress',
'SCRIPT_NAME': '',
'REQUEST_METHOD': 'GET',
'PATH_INFO': '/test/error',
'SERVER_PROTOCOL': 'HTTP/1.1',
'QUERY_STRING': 'aaa=1&bbb=2',
'paste.throw_errors': True,
'CONNECTION_TYPE': 'keep-alive',
'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
'SERVER_NAME': 'localhost',
'REMOTE_ADDR': '127.0.0.1',
'wsgi.url_scheme': 'http',
'SERVER_PORT': '6543',
'HTTP_HOST': 'localhost:6543',
'wsgi.multithread': True,
'HTTP_CACHE_CONTROL': 'max-age=0',
'HTTP_ACCEPT': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'wsgi.version': (1, 0),
'wsgi.run_once': False,
'wsgi.multiprocess': False,
'HTTP_ACCEPT_LANGUAGE': 'en-us,en;q=0.5',
'HTTP_ACCEPT_ENCODING': 'gzip, deflate'
}

class TestClientConfig(unittest.TestCase):

    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def test_empty_init(self):
        self.setUpClient()
        self.assertIsInstance(self.client, client.Client)

    def test_api_key(self):
        config = {'errormator.api_key':"ABCD"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['api_key'],
                         config['errormator.api_key'])

    def test_default_server(self):
        self.setUpClient()
        self.assertEqual(self.client.config['server_url'],
                         'https://api.errormator.com')

    def test_custom_server(self):
        config = {'errormator.server_url':"http://foo.bar.com"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['server_url'],
                         config['errormator.server_url'])

    def test_enabled_client(self):
        self.setUpClient()
        self.assertEqual(self.client.config['enabled'], True)

    def test_disabled_client(self):
        config = {'errormator':"false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['enabled'], False)

    def test_server_name(self):
        config = {'errormator.server_name':"some_name"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['server_name'],
                         config['errormator.server_name'])

    def test_default_server_name(self):
        import socket
        self.setUpClient()
        self.assertEqual(self.client.config['server_name'], socket.getfqdn())

    def test_client_name(self):
        config = {'errormator.client':"pythonX"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['client'],
                         config['errormator.client'])

    def test_default_client_name(self):
        self.setUpClient()
        self.assertEqual(self.client.config['client'], 'python')

    def test_default_timeout(self):
        self.setUpClient()
        self.assertEqual(self.client.config['timeout'], 10)

    def test_timeout(self):
        config = {'errormator.timeout':"5"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['timeout'], 5)

    def test_reraise_exceptions(self):
        config = {'errormator.reraise_exceptions':"false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['reraise_exceptions'], False)

    def test_default_reraise_exceptions(self):
        self.setUpClient()
        self.assertEqual(self.client.config['reraise_exceptions'], True)

    def test_default_slow_requests(self):
        self.setUpClient()
        self.assertEqual(self.client.config['slow_requests'], True)

    def test_disabled_slow_requests(self):
        config = {'errormator.reraise_exceptions':"false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['reraise_exceptions'], False)

    def test_default_slow_request_time(self):
        self.setUpClient()
        self.assertEqual(self.client.config['slow_request_time'],
                         datetime.timedelta(seconds=3))

    def test_custom_slow_request_time(self):
        config = {'errormator.slow_request.time':"2"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['slow_request_time'],
                         datetime.timedelta(seconds=2))

    def test_too_low_custom_slow_request_time(self):
        config = {'errormator.slow_request.time':"0.001"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['slow_request_time'],
                         datetime.timedelta(seconds=0.01))

    def test_default_logging(self):
        self.setUpClient()
        self.assertEqual(self.client.config['logging'], True)

    def test_custom_logging(self):
        config = {'errormator.logging':"false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['logging'], False)

    def test_default_logging_on_error(self):
        self.setUpClient()
        self.assertEqual(self.client.config['logging_on_error'], False)

    def test_custom_logging_on_error(self):
        config = {'errormator.logging_on_error':"true"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['logging_on_error'], True)

    def test_default_report_404(self):
        self.setUpClient()
        self.assertEqual(self.client.config['report_404'], False)

    def test_custom_report_404r(self):
        config = {'errormator.report_404':"true"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['report_404'], True)

    def test_default_report_errors(self):
        self.setUpClient()
        self.assertEqual(self.client.config['report_errors'], True)

    def test_custom_report_errors(self):
        config = {'errormator.report_errors':"false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['report_errors'], False)

    def test_default_buffer_flush_interval(self):
        self.setUpClient()
        self.assertEqual(self.client.config['buffer_flush_interval'], 5)

    def test_custom_buffer_flush_interval(self):
        config = {'errormator.buffer_flush_interval':"10"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['buffer_flush_interval'], 10)

    def test_default_force_send(self):
        self.setUpClient()
        self.assertEqual(self.client.config['force_send'], False)

    def test_custom_force_send(self):
        config = {'errormator.force_send':"1"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['force_send'], True)

    def test_default_request_keys_blacklist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['request_keys_blacklist'],
                ['password', 'passwd', 'pwd', 'auth_tkt', 'secret', 'csrf'])

    def test_custom_request_keys_blacklist(self):
        config = {'errormator.request_keys_blacklist':"aa,bb,cc"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['request_keys_blacklist'],
                         ['password', 'passwd', 'pwd', 'auth_tkt', 'secret',
                          'csrf', 'aa', 'bb', 'cc'])

    def test_default_environ_keys_whitelist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['environ_keys_whitelist'],
                ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE'])

    def test_custom_environ_keys_whitelist(self):
        config = {'errormator.environ_keys_whitelist':"aa,bb,cc"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['environ_keys_whitelist'],
                ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE',
                 'aa', 'bb', 'cc'])

    def test_default_log_namespace_blacklist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['log_namespace_blacklist'],
                ['errormator_client.client'])

    def test_custom_log_namespace_blacklist(self):
        config = {'errormator.log_namespace_blacklist':"aa,bb,cc.dd"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['log_namespace_blacklist'],
                ['aa', 'bb', 'cc.dd'])


#        self.filter_callable = config.get('errormator.filter_callable')
#        if self.filter_callable:
#            try:
#                parts = self.filter_callable.split(':')
#                _tmp = __import__(parts[0], globals(), locals(), [parts[1], ], -1)
#                self.filter_callable = getattr(_tmp, parts[1])
#            except ImportError as e:
#                self.filter_callable = self.data_filter
#                log.error('Could not import filter callable, using default, %s' % e)
#        else:
#            self.filter_callable = self.data_filter
#
#        if self.config['buffer_flush_interval'] < 1:
#            self.config['buffer_flush_interval'] = 1
#        # register logging
#        import errormator_client.logger
#        if self.config['logging']:
#            self.log_handler = errormator_client.logger.register_logging()
#            level = LEVELS.get(config.get('errormator.logging.level',
#                                      'NOTSET').lower(), logging.NOTSET)
#            self.log_handler.setLevel(level)
#
#        # register slow call metrics
#        if self.config['slow_requests']:
#            self.config['timing'] = config.get('errormator.timing', {})
#            for k, v in config.items():
#                if k.startswith('errormator.timing'):
#                    try:
#                        self.config['timing'][k[18:]] = float(v)
#                    except (TypeError, ValueError), e:
#                        self.config['timing'][k[18:]] = False
#            import errormator_client.timing
#            errormator_client.timing.register_timing(self.config)
#
#        self.endpoints = {
#                          "reports": '/api/reports',
#                          "slow_reports":'/api/slow_reports',
#                          "logs":'/api/logs',
#                          }










if __name__ == '__main__':
    unittest.main()  # pragma: nocover
