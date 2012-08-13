import unittest
import datetime
import logging
import socket
from errormator_client import client
from errormator_client.exceptions import get_current_traceback
from errormator_client.logger import register_logging



def example_filter_callable(structure, section=None):
    return 'filtered-data'

TEST_ENVIRON = {
                'bfg.routes.matchdict': {'action': u'error'},
'HTTP_COOKIE': 'country=US; http_referer="http://localhost:5000/"; test_group_id=5; sessionId=ec3ae5;',
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
'HTTP_ACCEPT_ENCODING': 'gzip, deflate',
'REMOTE_USER':'foo'
}

PARSED_REPORT_404 = {
                     'report_details': [{'username': '',
                        'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
                        'ip': '127.0.0.1',
                        'request': {'COOKIES': {u'country': u'US',
                                                u'sessionId': u'***',
                                                u'test_group_id': u'5',
                                                u'http_referer': u'http://localhost:5000/'},
                                    'POST': {},
                                    'GET': {u'aaa': [u'1'], u'bbb': [u'2']}},
                        'user_agent': u'', 'message': u''}],
                     'error_type': '404 Not Found',
                     'server': socket.getfqdn(), # different on every machine
                     'priority': 5,
                     'client': 'Python',
                     'http_status': 404}

PARSED_REPORT_500 = {'traceback': u'Traceback (most recent call last):', #this will be different everywhere
                     'report_details': [{'username': u'foo',
                                         'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
                                         'ip': '127.0.0.1',
                                         'request': {
                                                     'HTTP_ACCEPT': u'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                                     'COOKIES': {u'country': u'US',
                                                                 u'sessionId': u'***',
                                                                 u'test_group_id': u'5',
                                                                  u'http_referer': u'http://localhost:5000/'},
                                                     'SERVER_NAME': u'localhost',
                                                     'GET': {u'aaa': [u'1'], u'bbb': [u'2']},
                                                     'HTTP_ACCEPT_LANGUAGE': u'en-us,en;q=0.5',
                                                     'REMOTE_USER': u'foo',
                                                     'HTTP_HOST': u'localhost:6543',
                                                     'POST': {},
                                                     'HTTP_CACHE_CONTROL': u'max-age=0',
                                                     'HTTP_ACCEPT_ENCODING': u'gzip, deflate'},
                                         'user_agent': u'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
                                         'message': u''}],
                     'error_type': u'Exception: Test Exception',
                     'server': 'ergo-webreactor',
                     'priority': 5,
                     'client': 'Python',
                     'http_status': 500}

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
        self.assertEqual(self.client.config['buffer_flush_interval'],
                         datetime.timedelta(seconds=5))

    def test_custom_buffer_flush_interval(self):
        config = {'errormator.buffer_flush_interval':"10"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['buffer_flush_interval'],
                         datetime.timedelta(seconds=10))

    def test_custom_small_buffer_flush_interval(self):
        config = {'errormator.buffer_flush_interval':"0"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['buffer_flush_interval'],
                         datetime.timedelta(seconds=1))

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
                ['password', 'passwd', 'pwd', 'auth_tkt', 'secret', 'csrf',
                 'session'])

    def test_custom_request_keys_blacklist(self):
        config = {'errormator.request_keys_blacklist':"aa,bb,cc"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['request_keys_blacklist'],
                         ['password', 'passwd', 'pwd', 'auth_tkt', 'secret',
                          'csrf', 'session', 'aa', 'bb', 'cc'])

    def test_default_environ_keys_whitelist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['environ_keys_whitelist'],
                ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE',
                 'HTTP_REFERER'])

    def test_custom_environ_keys_whitelist(self):
        config = {'errormator.environ_keys_whitelist':"aa,bb,cc"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['environ_keys_whitelist'],
                ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE',
                 'HTTP_REFERER', 'aa', 'bb', 'cc'])

    def test_default_log_namespace_blacklist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['log_namespace_blacklist'],
                ['errormator_client.client'])

    def test_custom_log_namespace_blacklist(self):
        config = {'errormator.log_namespace_blacklist':"aa,bb,cc.dd"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['log_namespace_blacklist'],
                ['aa', 'bb', 'cc.dd'])

    def test_default_filter_callable(self):
        self.setUpClient()
        self.assertEqual(self.client.filter_callable, self.client.data_filter)

    def test_bad_filter_callable(self):
        config = {'errormator.filter_callable':"foo.bar.baz:callable_name"}
        self.setUpClient(config)
        self.assertEqual(self.client.filter_callable, self.client.data_filter)

    def test_custom_filter_callable(self):
        config = {'errormator.filter_callable':"errormator_client.tests:example_filter_callable"}
        self.setUpClient(config)
        self.assertEqual(self.client.filter_callable.__name__,
                         example_filter_callable.__name__)

    def test_default_logging_handler_present(self):
        self.setUpClient()
        self.assertEqual(hasattr(self.client, 'log_handler'), True)

    def test_custom_logging_handler_present(self):
        config = {'errormator.logging':"false"}
        self.setUpClient(config)
        self.assertEqual(hasattr(self.client, 'log_handler'), False)

    def test_default_logging_handler_level(self):
        self.setUpClient()
        self.assertEqual(self.client.log_handler.level, logging.NOTSET)

    def test_custom_logging_handler_level(self):
        config = {'errormator.logging.level':"CRITICAL"}
        self.setUpClient(config)
        self.assertEqual(self.client.log_handler.level, logging.CRITICAL)

    def test_default_timing_config(self):
        self.setUpClient()
        self.assertEqual(self.client.config['timing'], {})

    def test_timing_config_disable(self):
        config = {'errormator.timing.dbapi2_psycopg2':'false'}
        self.setUpClient(config)
        self.assertEqual(self.client.config['timing']['dbapi2_psycopg2'], False)

    def test_timing_config_custom(self):
        config = {'errormator.timing.dbapi2_psycopg2':'5'}
        self.setUpClient(config)
        self.assertEqual(self.client.config['timing']['dbapi2_psycopg2'], 5)

    def test_timing_config_mixed(self):
        config = {'errormator.timing.dbapi2_psycopg2':'5',
                  'errormator.timing':{'urllib':11, 'dbapi2_oursql':6}
                  }
        self.setUpClient(config)
        self.assertEqual(self.client.config['timing']['dbapi2_psycopg2'], 5)
        self.assertEqual(self.client.config['timing']['dbapi2_oursql'], 6)
        self.assertEqual(self.client.config['timing']['urllib'], 11)

def generate_error():
    pass

class TestClientSending(unittest.TestCase):

    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def test_check_if_deliver_false(self):
        self.setUpClient()
        self.assertEqual(self.client.check_if_deliver(), False)

    def test_check_if_deliver_forced(self):
        self.setUpClient()
        self.assertEqual(self.client.check_if_deliver(force_send=True), True)


class TestErrorParsing(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def test_py_report_404(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404)
        self.assertEqual(self.client.report_queue[0], PARSED_REPORT_404)

    def test_py_report_500_no_traceback(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=500)
        bogus_500_report = PARSED_REPORT_404.copy()
        bogus_500_report['http_status'] = 500
        bogus_500_report['error_type'] = 'Unknown'
        self.assertEqual(self.client.report_queue[0], bogus_500_report)

    def test_py_report_500_traceback(self):
        self.setUpClient()
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
        self.client.py_report(TEST_ENVIRON, traceback=traceback,
                              http_status=500)
        self.client.report_queue[0]['traceback'] = 'Traceback (most recent call last):'
        self.assertEqual(self.client.report_queue[0], PARSED_REPORT_500)

class TestLogs(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def test_py_log(self):
        self.setUpClient()
        handler = register_logging()
        logger = logging.getLogger('testing')
        logger.critical('test entry')
        self.client.py_log(TEST_ENVIRON, records=handler.get_records())
        fake_log = {'log_level': 'CRITICAL',
                     'namespace': 'testing',
                     'server': 'test-foo', # this will be different everywhere
                     'request_id': None,
                     'date': '2012-08-13T21:20:37.418.307066',
                     'message': 'test entry'}
        # update fields depenand on machine
        self.client.log_queue[0]['date'] = fake_log['date']
        self.client.log_queue[0]['server'] = fake_log['server']
        self.assertEqual(self.client.log_queue[0], fake_log)

class TestSending(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def test_send_error_failure(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404)
        self.client.submit_report_data()
        self.assertEqual(self.client.report_queue, [])

if __name__ == '__main__':
    unittest.main()  # pragma: nocover
