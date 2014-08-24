# -*- coding: utf-8 -*-
import copy
import datetime
import logging
import socket
import time
import unittest

import pkg_resources
from webob import Request

from appenlight_client import client, make_appenlight_middleware
from appenlight_client.exceptions import get_current_traceback
from appenlight_client.logger import register_logging
from appenlight_client.wsgi import AppenlightWSGIWrapper
from appenlight_client.utils import fullyQualifiedName


fname = pkg_resources.resource_filename('appenlight_client',
                                        'templates/default_template.ini')
timing_conf = client.get_config(path_to_config=fname)
# set api key

for k, v in timing_conf.iteritems():
    if 'appenlight.timing' in k:
        timing_conf[k] = 0.0000001

timing_conf.pop('appenlight.timing.dbapi2_sqlite3', None)

# this sets up timing decoration for us
client.Client(config=timing_conf)
from appenlight_client.timing import local_timing, get_local_storage, time_trace


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
    'REMOTE_USER': 'foo'
}

REQ_START_TIME = datetime.datetime.utcnow()
REQ_END_TIME = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
SERVER_NAME = socket.getfqdn()  # different on every machine

PARSED_REPORT_404 = {
    'report_details': [{'username': u'foo',
                        'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
                        'ip': '127.0.0.1',
                        'start_time': REQ_START_TIME,
                        'slow_calls': [],
                        'request': {'COOKIES': {u'country': u'US',
                                                u'sessionId': u'***',
                                                u'test_group_id': u'5',
                                                u'http_referer': u'http://localhost:5000/'},
                                    'POST': {},
                                    'GET': {u'aaa': [u'1'], u'bbb': [u'2']},
                                    'HTTP_METHOD': 'GET',
                        },
                        'user_agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
                        'message': u'',
                        'end_time': REQ_END_TIME,
                        'request_stats': {}
                       }],
    'error': '404 Not Found',
    'server': SERVER_NAME,
    'priority': 5,
    'client': 'appenlight-python',
    'language':'python',
    'http_status': 404}

PARSED_REPORT_500 = {'traceback': u'Traceback (most recent call last):',
                     # this will be different everywhere
                     'report_details': [{'traceback': [
                         {'cline': u"raise Exception('Test Exception')",
                          'file': 'appenlight_client/tests.py',
                          'fn': 'test_py_report_500_traceback',
                          'line': 454,
                          'vars': []},
                         {'cline': u'Exception: Test Exception',
                          'file': '',
                          'fn': '',
                          'line': '',
                          'vars': []}],
                                         'username': u'foo',
                                         'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
                                         'ip': '127.0.0.1',
                                         'start_time': REQ_START_TIME,
                                         'slow_calls': [],
                                         'request': {
                                             'HTTP_ACCEPT': u'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                             'COOKIES': {u'country': u'US',
                                                         u'sessionId': u'***',
                                                         u'test_group_id': u'5',
                                                         u'http_referer': u'http://localhost:5000/'},
                                             'SERVER_NAME': u'localhost',
                                             'GET': {u'aaa': [u'1'],
                                                     u'bbb': [u'2']},
                                             'HTTP_ACCEPT': u'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                             'HTTP_ACCEPT_ENCODING': u'gzip, deflate',
                                             'HTTP_ACCEPT_LANGUAGE': u'en-us,en;q=0.5',
                                             'HTTP_CACHE_CONTROL': u'max-age=0',
                                             'HTTP_HOST': u'localhost:6543',
                                             'HTTP_METHOD': 'GET',
                                             'REMOTE_USER': u'foo',
                                             'HTTP_HOST': u'localhost:6543',
                                             'POST': {},
                                             'HTTP_CACHE_CONTROL': u'max-age=0',
                                             'HTTP_ACCEPT_ENCODING': u'gzip, deflate',
                                             'HTTP_METHOD': 'GET'},
                                         'user_agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
                                         'message': u'',
                                         'end_time': REQ_END_TIME,
                                         'request_stats': {}}],
                     'error': u'Exception: Test Exception',
                     'server': SERVER_NAME,
                     'priority': 5,
                     'client': 'appenlight-python',
                     'language':'python',
                     'http_status': 500}

PARSED_SLOW_REPORT = {
    'report_details': [{'username': u'foo',
                        'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
                        'ip': '127.0.0.1',
                        'start_time': REQ_START_TIME,
                        'slow_calls': [],
                        'request': {'COOKIES': {u'country': u'US',
                                                u'sessionId': u'***',
                                                u'test_group_id': u'5',
                                                u'http_referer': u'http://localhost:5000/'},
                                    'POST': {},
                                    'GET': {u'aaa': [u'1'], u'bbb': [u'2'], },
                                    'HTTP_ACCEPT': u'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'HTTP_ACCEPT_ENCODING': u'gzip, deflate',
                                    'HTTP_ACCEPT_LANGUAGE': u'en-us,en;q=0.5',
                                    'HTTP_CACHE_CONTROL': u'max-age=0',
                                    'HTTP_HOST': u'localhost:6543',
                                    'HTTP_METHOD': 'GET',
                                    'REMOTE_USER': u'foo',
                                    'SERVER_NAME': u'localhost',
                        },
                        'user_agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
                        'message': u'',
                        'end_time': REQ_END_TIME,
                        'request_stats': {}}],
    'error': '',
    'server': SERVER_NAME,
    'priority': 5,
    'client': 'appenlight-python',
    'language':'python',
    'http_status': 200}


class TestClientConfig(unittest.TestCase):
    def setUpClient(self, config=None):
        if config is None:
            config = {'appenlight.api_key': '12345'}
        self.client = client.Client(config)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_empty_init(self):
        self.setUpClient()
        self.assertIsInstance(self.client, client.Client)

    def test_api_key(self):
        config = {'appenlight.api_key': '12345AAAAA'}
        self.setUpClient(config)
        self.assertEqual(self.client.config['api_key'],
                         config['appenlight.api_key'])

    def test_default_transport(self):
        self.setUpClient()
        self.assertEqual(self.client.config['transport'],
                         'appenlight_client.transports.requests:HTTPTransport')

    def test_transport_config(self):
        config = {
            'appenlight.transport_config': 'https://api.appenlight.com?threaded=0&timeout=10'}
        self.setUpClient(config)
        self.assertDictContainsSubset({'url': 'https://api.appenlight.com',
                                       'timeout': 10, 'threaded': 0},
                                      self.client.transport.transport_config)

    def test_enabled_client(self):
        self.setUpClient()
        self.assertEqual(self.client.config['enabled'], True)

    def test_disabled_client(self):
        config = {'appenlight': "false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['enabled'], False)

    def test_disabled_client_no_key(self):
        self.setUpClient({})
        self.assertEqual(self.client.config['enabled'], False)

    def test_server_name(self):
        config = {'appenlight.server_name': "some_name"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['server_name'],
                         config['appenlight.server_name'])

    def test_default_server_name(self):
        self.setUpClient()
        self.assertEqual(self.client.config['server_name'], socket.getfqdn())

    def test_client_name(self):
        config = {'appenlight.client': "pythonX"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['client'],
                         config['appenlight.client'])

    def test_default_client_name(self):
        self.setUpClient()

        self.assertEqual(self.client.config['client'], 'python3' if client.PY3 \
            else 'python')

    def test_reraise_exceptions(self):
        config = {'appenlight.reraise_exceptions': "false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['reraise_exceptions'], False)

    def test_default_reraise_exceptions(self):
        self.setUpClient()
        self.assertEqual(self.client.config['reraise_exceptions'], True)

    def test_default_slow_requests(self):
        self.setUpClient()
        self.assertEqual(self.client.config['slow_requests'], True)

    def test_disabled_slow_requests(self):
        config = {'appenlight.reraise_exceptions': "false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['reraise_exceptions'], False)

    def test_default_slow_request_time(self):
        self.setUpClient()
        self.assertEqual(self.client.config['slow_request_time'],
                         datetime.timedelta(seconds=1))

    def test_custom_slow_request_time(self):
        config = {'appenlight.slow_request_time': "2"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['slow_request_time'],
                         datetime.timedelta(seconds=2))

    def test_too_low_custom_slow_request_time(self):
        config = {'appenlight.slow_request_time': "0.001"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['slow_request_time'],
                         datetime.timedelta(seconds=0.01))

    def test_default_logging(self):
        self.setUpClient()
        self.assertEqual(self.client.config['logging'], True)

    def test_custom_logging(self):
        config = {'appenlight.logging': "false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['logging'], False)

    def test_default_logging_on_error(self):
        self.setUpClient()
        self.assertEqual(self.client.config['logging_on_error'], False)

    def test_custom_logging_on_error(self):
        config = {'appenlight.logging_on_error': "true"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['logging_on_error'], True)

    def test_default_report_404(self):
        self.setUpClient()
        self.assertEqual(self.client.config['report_404'], False)

    def test_custom_report_404r(self):
        config = {'appenlight.report_404': "true"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['report_404'], True)

    def test_default_report_errors(self):
        self.setUpClient()
        self.assertEqual(self.client.config['report_errors'], True)

    def test_custom_report_errors(self):
        config = {'appenlight.report_errors': "false"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['report_errors'], False)

    def test_default_buffer_flush_interval(self):
        self.setUpClient()
        self.assertEqual(self.client.config['buffer_flush_interval'],
                         datetime.timedelta(seconds=5))

    def test_custom_buffer_flush_interval(self):
        config = {'appenlight.buffer_flush_interval': "10"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['buffer_flush_interval'],
                         datetime.timedelta(seconds=10))

    def test_custom_small_buffer_flush_interval(self):
        config = {'appenlight.buffer_flush_interval': "0"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['buffer_flush_interval'],
                         datetime.timedelta(seconds=1))

    def test_default_buffer_clear_on_send(self):
        self.setUpClient()
        self.assertEqual(self.client.config['buffer_clear_on_send'],
                         False)

    def test_custom_buffer_clear_on_send(self):
        config = {'appenlight.buffer_clear_on_send': "true"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['buffer_clear_on_send'],
                         True)

    def test_default_force_send(self):
        self.setUpClient()
        self.assertEqual(self.client.config['force_send'], False)

    def test_custom_force_send(self):
        config = {'appenlight.force_send': "1"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['force_send'], True)

    def test_default_request_keys_blacklist(self):
        self.setUpClient()
        self.assertItemsEqual(self.client.config['request_keys_blacklist'],
                              ['password', 'passwd', 'pwd', 'auth_tkt',
                               'secret',
                               'csrf', 'xsrf', 'auth',
                               'session', 'pass', 'config', 'settings',
                               'environ'])

    def test_custom_request_keys_blacklist(self):
        config = {'appenlight.request_keys_blacklist': "aa,bb,cc"}
        self.setUpClient(config)
        self.assertItemsEqual(self.client.config['request_keys_blacklist'],
                              ['password', 'passwd', 'pwd', 'auth_tkt',
                               'secret',
                               'csrf', 'xsrf', 'auth', 'session', 'pass',
                               'config', 'settings',
                               'environ', 'aa', 'bb', 'cc'])

    def test_default_environ_keys_whitelist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['environ_keys_whitelist'],
                         ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME',
                          'CONTENT_TYPE',
                          'HTTP_REFERER'])

    def test_custom_environ_keys_whitelist(self):
        config = {'appenlight.environ_keys_whitelist': "aa,bb,cc"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['environ_keys_whitelist'],
                         ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME',
                          'CONTENT_TYPE',
                          'HTTP_REFERER', 'aa', 'bb', 'cc'])

    def test_default_log_namespace_blacklist(self):
        self.setUpClient()
        self.assertEqual(self.client.config['log_namespace_blacklist'],
                         ['appenlight_client.client',
                          'appenlight_client.transports.requests'])

    def test_custom_log_namespace_blacklist(self):
        config = {'appenlight.log_namespace_blacklist': "aa,bb,cc.dd"}
        self.setUpClient(config)
        self.assertEqual(self.client.config['log_namespace_blacklist'],
                         ['appenlight_client.client',
                          'appenlight_client.transports.requests',
                          'aa', 'bb', 'cc.dd'])

    def test_default_filter_callable(self):
        self.setUpClient()
        self.assertEqual(self.client.filter_callable, self.client.data_filter)

    def test_bad_filter_callable(self):
        config = {'appenlight.filter_callable': "foo.bar.baz:callable_name"}
        self.setUpClient(config)
        self.assertEqual(self.client.filter_callable, self.client.data_filter)

    def test_custom_filter_callable(self):
        config = {'appenlight.filter_callable':
                      "appenlight_client.tests:example_filter_callable"}
        self.setUpClient(config)
        self.assertEqual(self.client.filter_callable.__name__,
                         example_filter_callable.__name__)

    def test_default_logging_handler_present(self):
        self.setUpClient()
        self.assertEqual(hasattr(self.client, 'log_handler'), True)

    def test_custom_logging_handler_present(self):
        config = {'appenlight.logging': "false"}
        self.setUpClient(config)
        self.assertEqual(hasattr(self.client, 'log_handler'), False)

    def test_default_logging_handler_level(self):
        self.setUpClient()
        self.assertEqual(self.client.log_handler.level, logging.WARNING)

    def test_custom_logging_handler_level(self):
        config = {'appenlight.logging.level': "CRITICAL",
                  'appenlight.api_key': '12345'}
        self.setUpClient(config)
        self.assertEqual(self.client.log_handler.level, logging.CRITICAL)

    def test_default_timing_config(self):
        self.setUpClient()
        self.assertEqual(self.client.config['timing'], {})

    def test_timing_config_disable(self):
        config = {'appenlight.timing.dbapi2_psycopg2': 'false',
                  'appenlight.api_key': '12345'}
        self.setUpClient(config)
        self.assertEqual(self.client.config['timing']['dbapi2_psycopg2'],
                         False)

    def test_timing_config_custom(self):
        config = {'appenlight.timing.dbapi2_psycopg2': '5',
                  'appenlight.api_key': '12345'}
        self.setUpClient(config)
        self.assertEqual(self.client.config['timing']['dbapi2_psycopg2'], 5)

    def test_timing_config_mixed(self):
        config = {'appenlight.timing.dbapi2_psycopg2': '5',
                  'appenlight.timing': {'urllib': 11, 'dbapi2_oursql': 6},
                  'appenlight.api_key': '12345'
        }
        self.setUpClient(config)
        self.assertEqual(self.client.config['timing']['dbapi2_psycopg2'], 5)
        self.assertEqual(self.client.config['timing']['dbapi2_oursql'], 6)
        self.assertEqual(self.client.config['timing']['urllib'], 11)


def generate_error():
    pass


class TestClientTransport(unittest.TestCase):
    def setUpClient(self, config={'appenlight.api_key': 'blargh!'}):
        self.client = client.Client(config)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_check_if_deliver_false(self):
        self.setUpClient()
        self.client.last_submit = datetime.datetime.now()
        self.assertEqual(self.client.check_if_deliver(), False)

    def test_check_if_deliver_forced(self):
        self.setUpClient()
        self.client.log_queue = ['dummy']
        self.assertEqual(self.client.check_if_deliver(force_send=True), True)

    def test_send_error_failure_queue(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404)
        self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        self.assertEqual(self.client.report_queue, [])

    def test_http_transport_failure(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        self.assertEqual(result, False)

    def test_http_transport_success(self):
        # requires valid key for test
        return True
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://127.0.0.1:6543?threaded=1&timeout=5'})
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        self.assertEqual(result, True)

    def test_http_transport_timeout(self):
        # requires valid key for test
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://127.0.0.1:6543?threaded=1&timeout=0.0001'})
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        self.assertEqual(result, False)

    def test_wrong_server_failure(self):
        # requires valid key for test
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5'})
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        self.assertEqual(result, False)

    def test_default_buffer_clear(self):
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5'})
        for x in xrange(10):
            self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        assert len(self.client.report_queue) == 0

    def test_default_buffer_non_empty(self):
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5'})
        for x in xrange(255):
            self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        assert len(self.client.report_queue) > 0

    def test_custom_buffer_clear(self):
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5',
             'appenlight.buffer_clear_on_send': "true"
            })
        for x in xrange(255):
            self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        assert len(self.client.report_queue) == 0


class TestErrorParsing(unittest.TestCase):
    def setUpClient(self, config={'appenlight.report_local_vars': False}):
        self.client = client.Client(config)
        self.maxDiff = None

    def test_py_report_404(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404,
                              start_time=REQ_START_TIME, end_time=REQ_END_TIME)
        self.assertDictContainsSubset(PARSED_REPORT_404,
                                      self.client.report_queue[0])

    def test_py_report_500_no_traceback(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=500,
                              start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        bogus_500_report = copy.deepcopy(PARSED_REPORT_500)
        bogus_500_report['http_status'] = 500
        bogus_500_report['error'] = ''
        del bogus_500_report['traceback']
        del bogus_500_report['report_details'][0]['traceback']
        bogus_500_report['report_details'][0]['request_stats'] = {}
        self.assertDictContainsSubset(bogus_500_report,
                                      self.client.report_queue[0])

    def test_py_report_500_traceback(self):
        self.setUpClient()
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
        self.client.py_report(TEST_ENVIRON, traceback=traceback,
                              http_status=500,
                              start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        self.client.report_queue[0]['traceback'] = \
            'Traceback (most recent call last):'
        line_no = \
            self.client.report_queue[0]['report_details'][0]['traceback'][0]['line']
        assert int(line_no) > 0
        # set line number to match as this will change over time
        PARSED_REPORT_500['report_details'][0]['traceback'][0]['line'] = line_no
        self.assertDictContainsSubset(PARSED_REPORT_500, self.client.report_queue[0])

    def test_frameinfo(self):
        self.setUpClient(config={'appenlight.report_local_vars': 'true'})
        test = 1
        b = {1: 'a', '2': 2, 'ccc': 'ddd'}
        obj = object()
        e_obj = client.Client({})
        unic = 'grzegżółka'
        a_list = [1, 2, 4, 5, 6, client.Client({}), 'dupa']
        long_val = 'imlong' * 100
        datetest = datetime.datetime.utcnow()
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
        self.client.py_report(TEST_ENVIRON, traceback=traceback,
                              http_status=500)
        assert len(self.client.report_queue[0]['report_details'][0]['traceback'][0]['vars']) == 9


class TestLogs(unittest.TestCase):
    def setUpClient(self, config={}):
        timing_conf['appenlight.api_key'] = '12345'
        config = {'appenlight.api_key': '12345'}
        self.client = client.Client(config)
        self.maxDiff = None

    def test_py_log(self):
        self.setUpClient()
        handler = register_logging()
        logger = logging.getLogger('testing')
        logger.critical('test entry')
        self.client.py_log(TEST_ENVIRON, records=handler.get_records())
        fake_log = {'log_level': 'CRITICAL',
                    'namespace': 'testing',
                    'server': 'test-foo',  # this will be different everywhere
                    'request_id': None,
                    'date': '2012-08-13T21:20:37.418.307066',
                    'message': 'test entry'}
        # update fields depenand on machine
        self.client.log_queue[0]['date'] = fake_log['date']
        self.client.log_queue[0]['server'] = fake_log['server']
        self.assertEqual(self.client.log_queue[0], fake_log)

    def test_ignore_self_logs(self):
        self.setUpClient()
        handler = register_logging()
        self.client.py_report(TEST_ENVIRON, http_status=500)
        self.client.py_report(TEST_ENVIRON, start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        self.client.py_log(TEST_ENVIRON, records=handler.get_records())
        self.assertEqual(len(self.client.log_queue), 0)


class TestSlowReportParsing(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def test_py_report_slow(self):
        self.setUpClient()
        self.maxDiff = None
        self.client.py_report(TEST_ENVIRON, start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        self.assertDictContainsSubset(PARSED_SLOW_REPORT,
                                      self.client.report_queue[0])


class TestMakeMiddleware(unittest.TestCase):
    def test_make_middleware(self):
        def app(environ, start_response):
            start_response('200 OK', [('content-type', 'text/html')])
            return ['Hello world!']

        app = make_appenlight_middleware(app, {'appenlight.api_key': '12345'})
        self.assertTrue(isinstance(app, AppenlightWSGIWrapper))

    def test_make_middleware_disabled(self):
        def app(environ, start_response):
            start_response('200 OK', [('content-type', 'text/html')])
            return ['Hello world!']

        app = make_appenlight_middleware(app, {'appenlight': 'false'})
        self.assertFalse(isinstance(app, AppenlightWSGIWrapper))


class TestCustomTiming(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_custom_time_trace(self):
        @time_trace(name='foo_func', min_duration=0.1)
        def foo(arg):
            time.sleep(0.2)
            return arg

        foo('a')
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_custom_nested_timimg(self):
        @time_trace(name='baz_func', min_duration=0.1)
        def baz(arg):
            time.sleep(0.12)
            return arg

        @time_trace(name='foo_func', min_duration=0.1)
        def foo(arg):
            time.sleep(0.12)
            return baz(arg)

        @time_trace(name='bar_func', min_duration=0.1)
        def bar(arg):
            return foo(arg)

        bar('a')
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 3)


class TestTimingHTTPLibs(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_urllib_URLOpener_open(self):
        import urllib

        opener = urllib.URLopener()
        opener.open("http://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_urllib_urlretrieve(self):
        import urllib

        urllib.urlretrieve("http://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_urllib2(self):
        import urllib2

        urllib2.urlopen("http://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_urllib3(self):
        try:
            import urllib3
        except ImportError:
            return
        http = urllib3.PoolManager()
        http.request('GET', "http://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_requests(self):
        try:
            import requests
        except ImportError:
            return
        requests.get("http://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_httplib(self):
        import httplib

        h2 = httplib.HTTPConnection("www.ubuntu.com")
        h2.request("GET", "/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)


class TestRedisPY(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_redis_py_command(self):
        try:
            import redis
        except ImportError:
            return

        client = redis.StrictRedis()
        client.setex('testval', 10, 'foo')
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)


class TestMemcache(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_memcache_command(self):
        try:
            import memcache
        except ImportError:
            return
        mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        mc.set("some_key", "Some value")
        value = mc.get("some_key")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)


class TestPylibMc(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_memcache_command(self):
        # TODO: not finished
        return
        try:
            import pylibmc
        except ImportError:
            return
        mc = pylibmc.Client(['127.0.0.1:11211'])
        mc.set("some_key", "Some value")
        value = mc.get("some_key")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)


class TestDBApi2Drivers(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        timing_conf['appenlight.timing.dbapi2_sqlite3'] = 0.0000000001
        self.setUpClient(timing_conf)
        self.stmt = '''SELECT 1+2+3 as result'''

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_sqlite(self):
        try:
            import sqlite3
        except ImportError:
            return
        conn = sqlite3.connect(':memory:')
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_sqlite_call_number(self):
        try:
            import sqlite3
        except ImportError:
            return
        conn = sqlite3.connect(':memory:')
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()
        c.execute(self.stmt)
        c.fetchone()
        c.execute(self.stmt)
        c.fetchone()
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(int(stats['sql_calls']), 4)

    def test_psycopg2(self):
        try:
            import psycopg2
        except ImportError:
            return
        conn = psycopg2.connect(
            "user=test host=127.0.0.1 dbname=test password=test")
        c = conn.cursor()
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, c)
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_pg8000(self):
        try:
            import pg8000
        except ImportError:
            return
        conn = pg8000.DBAPI.connect(host="127.0.0.1", user="test",
                                    password="test")
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_postgresql(self):
        try:
            import postgresql
        except ImportError:
            return
        conn = postgresql.open('pq://test:test@localhost')
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()[0]
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_mysqldb(self):
        try:
            import MySQLdb
        except ImportError:
            return
        conn = MySQLdb.connect(passwd="test", user="test", host="127.0.0.1",
                               port=3306)
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_oursql(self):
        try:
            import oursql
        except ImportError:
            return
        conn = oursql.connect(passwd="test", user="test")
        c = conn.cursor(oursql.DictCursor)
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_odbc(self):
        try:
            import pyodbc
        except ImportError:
            return
        conn = pyodbc.connect(
            'Driver={MySQL};Server=127.0.0.1;Port=3306;Database=information_schema;User=test; Password=test;Option=3;')
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)

    def test_pymysql(self):
        try:
            import pymysql
        except ImportError:
            return
        conn = pymysql.connect(host='127.0.0.1', user='test', passwd='test')
        c = conn.cursor()
        c.execute(self.stmt)
        c.fetchone()
        c.close()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 2)


class TestMako(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(timing_conf)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_render(self):
        try:
            import mako
        except ImportError:
            return
        template = mako.template.Template('''
        <%
        import time
        time.sleep(0.01)
        %>
        xxxxx ${1+2} yyyyyy
        ''')
        template.render()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_render_call_number(self):
        try:
            import mako
        except ImportError:
            return
        template = mako.template.Template('''
        <%
        import time
        time.sleep(0.01)
        %>
        xxxxx ${1+2} yyyyyy
        ''')
        template.render()
        template.render()
        template.render()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(stats['tmpl_calls'], 3)

    def test_render_unicode(self):
        try:
            import mako
        except ImportError:
            return
        template = mako.template.Template(u'''
        <%
        import time
        time.sleep(0.01)
        %>
        xxxxx ${1+2} yyyyyy
        ''')
        template.render_unicode()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)

    def test_template_lookup(self):
        try:
            from mako.lookup import TemplateLookup
        except ImportError:
            return
        lookup = TemplateLookup()
        lookup.put_string("base.html", '''
        <%
        import time
        time.sleep(0.02)
        %>
            <html><body><%include file="subtemplate.html"/></body></html>
        ''')
        lookup.put_string("subtemplate.html", '''
        <%
        import time
        time.sleep(0.02)
        %>
            SUBTEPLATE
        ''')
        template = lookup.get_template("base.html")
        template.render_unicode()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)


class TestChameleon(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_render(self):
        # TODO: This timer doesnt work for now
        return True
        try:
            import chameleon.zpt
        except ImportError:
            return
        import time

        template = chameleon.zpt.PageTemplate('''
        ${sleep(0.06)}
        xxxxx ${1+2} yyyyyy
        ''')
        template.render(sleep=time.sleep)
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)


class TestJinja2(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_render(self):
        try:
            import jinja2
        except ImportError:
            return
        import time

        template = jinja2.Template('''
        {{sleep(0.06)}}
        xxxxx {{1+2}} yyyyyy
        ''')
        template.render(sleep=time.sleep)
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)


class TestDjangoTemplates(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(config)

    def setUp(self):
        self.setUpClient(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_render(self):
        try:
            from django import template
        except ImportError:
            return
        from django.conf import settings

        settings.configure(TEMPLATE_DIRS=("/whatever/templates",))
        import time

        ctx = template.Context()
        ctx.update({'time': lambda: time.sleep(0.06)})
        template = template.Template('''
        xxxxx {{ time }} yyyyyy
        ''')
        template.render(ctx)
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertEqual(len(result), 1)


class WSGITests(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_normal_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 0)

    def test_normal_request_decorator(self):
        from appenlight_client.client import decorate

        @decorate(appenlight_config={'appenlight.api_key': '12345'})
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 0)

    def test_error_request_decorator(self):
        from appenlight_client.client import decorate

        @decorate(appenlight_config={'appenlight.api_key': '12345',
                                     'appenlight.reraise_exceptions': False})
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        app.appenlight_client.last_submit = datetime.datetime.now()
        req = Request.blank('http://localhost/test')
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 1)

    def test_error_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 1)
        self.assertEqual(app.appenlight_client.report_queue[0]['http_status'],
                         500)


    def test_not_found_request(self):
        def app(environ, start_response):
            start_response('404 Not Found', [('Content-Type', 'text/html')])
            try:
                raise Exception('something wrong')
            except Exception, e:
                pass
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['report_404'] = True
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 1)
        self.assertEqual(app.appenlight_client.report_queue[0]['http_status'],
                         404)

    def test_ignored_error_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        req.environ['appenlight.ignore_error'] = 1
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 0)

    def test_view_name_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            environ['appenlight.view_name'] = 'foo:app'
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertEqual(app.appenlight_client.report_queue[0].get('view_name'),
                         'foo:app')

    def test_slow_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            time.sleep(1.1)
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 1)

    def test_ignored_slow_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            time.sleep(1.1)
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        req.environ['appenlight.ignore_slow'] = 1
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertEqual(len(app.appenlight_client.report_queue), 0)

    def test_logging_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            logging.warning('test logging')
            logging.critical('test logging critical')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertGreaterEqual(len(app.appenlight_client.log_queue), 2)

    def test_timing_request(self):
        try:
            import psycopg2
        except ImportError:
            return

        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])

            @time_trace(name='foo_func', min_duration=0.1)
            def foo(arg):
                time.sleep(0.2)
                return arg

            foo('a')
            time.sleep(0.1)
            conn = psycopg2.connect(
                "user=test host=127.0.0.1 dbname=test password=test")
            c = conn.cursor()
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, c)
            c.execute('SELECT 1, pg_sleep(0.5)')
            c.fetchone()
            c.close()
            conn.close()
            return ['Hello World!']

        get_local_storage(local_timing).clear()
        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        req.get_response(app)
        stats, result = get_local_storage(local_timing).get_thread_stats()
        self.assertGreater(stats['main'], 0)
        self.assertGreater(stats['sql'], 0)

    def test_multiple_post_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test', POST=[("a","a"), ("b","2"), ("b","1")])
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.last_submit = datetime.datetime.now()
        req.get_response(app)
        self.assertDictEqual({'a': u'a', 'b': [u'2', u'1']},
                             app.appenlight_client.report_queue[0]['report_details'][0]['request']['POST'])


class CallableNameTests(unittest.TestCase):
    def setUpClient(self, config={}):
        self.client = client.Client(timing_conf)

    def tearDown(self):
        get_local_storage(local_timing).clear()

    def test_func(self):
        def some_call():
            return 1

        fullyQualifiedName(some_call)
        some_call()
        self.assertEqual(some_call._appenlight_name,
                         'appenlight_client/tests:some_call')

    def test_newstyle_class(self):
        class Foo(object):
            def test(self):
                return 1

            def __call__(self):
                return 2

        fullyQualifiedName(Foo)
        fullyQualifiedName(Foo.test)
        self.assertEqual(Foo._appenlight_name, 'appenlight_client/tests:Foo')
        self.assertEqual(Foo.test._appenlight_name,
                         'appenlight_client/tests:Foo.test')

    def test_oldstyle_class(self):
        class Bar():
            def test(self):
                return 1

            def __call__(self):
                return 2

        fullyQualifiedName(Bar)
        fullyQualifiedName(Bar.test)
        self.assertEqual(Bar._appenlight_name, 'appenlight_client/tests:Bar')
        self.assertEqual(Bar.test._appenlight_name,
                         'appenlight_client/tests:Bar.test')


if __name__ == '__main__':
    unittest.main()  # pragma: nocover
