# -*- coding: utf-8 -*-
import copy
import datetime
import logging
import socket
import time
import random
import pprint

import pkg_resources
from webob import Request

from appenlight_client import client, make_appenlight_middleware
from appenlight_client.exceptions import get_current_traceback
from appenlight_client.ext.logging import register_logging
from appenlight_client.wsgi import AppenlightWSGIWrapper
from appenlight_client.utils import fullyQualifiedName, import_from_module, filter_callable


logging.basicConfig()

fname = pkg_resources.resource_filename('appenlight_client',
                                        'templates/default_template.ini')
timing_conf = client.get_config(path_to_config=fname)
# set api key

for k, v in timing_conf.iteritems():
    if 'appenlight.timing' in k:
        timing_conf[k] = 0.0000001

timing_conf.pop('appenlight.timing.dbapi2_sqlite3', None)

# this sets up timing decoration for us
global_client = client.BaseClient(config=timing_conf)
global_client.unregister_logger()
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
    'error': '404 Not Found',
    'server': SERVER_NAME,
    'priority': 5,
    'client': 'appenlight-python',
    'language': 'python',
    'username': u'foo',
     'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
     'ip': '127.0.0.1',
     'start_time': REQ_START_TIME,
     'slow_calls': [],
     'request': {'COOKIES': {},
                 'POST': {},
                 'GET': {u'aaa': [u'1'], u'bbb': [u'2']},
                 'HTTP_METHOD': 'GET',
                 },
     'user_agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
     'message': u'',
     'end_time': REQ_END_TIME,
     'request_stats': {},
    'http_status': 404}

PARSED_REPORT_500 = {
                     # this will be different everywhere
                     'error': u'Exception: Test Exception',
                     'server': SERVER_NAME,
                     'priority': 5,
                     'client': 'appenlight-python',
                     'language': 'python',
                     'traceback': [
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
                         'COOKIES': {},
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
                     'request_stats': {},
                     'http_status': 500}

PARSED_SLOW_REPORT = {
    'error': '',
    'server': SERVER_NAME,
    'priority': 5,
    'client': 'appenlight-python',
    'language': 'python',
    'username': u'foo',
    'url': 'http://localhost:6543/test/error?aaa=1&bbb=2',
    'ip': '127.0.0.1',
    'start_time': REQ_START_TIME,
    'slow_calls': [],
    'request': {'COOKIES': {},
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
    'request_stats': {},
    'http_status': 200}

class BaseTest(object):

    def setUpClient(self, config=None):
        timing_conf['appenlight.api_key'] = 'default_test_key'
        if config is None:
            config = {'appenlight.api_key': 'default_test_key'}
        self.client = client.BaseClient(config)

    def teardown_method(self, method):
        storage = get_local_storage(local_timing)
        storage.clear()
        if hasattr(self, 'client'):
            self.client.purge_data()
            self.client.unregister_logger()


class TestClientConfig(BaseTest):


    def test_empty_init(self):
        self.setUpClient()
        assert isinstance(self.client, (client.Client, client.BaseClient))

    def test_api_key(self):
        config = {'appenlight.api_key': '12345AAAAA'}
        self.setUpClient(config)
        assert self.client.config['api_key'] == config['appenlight.api_key']

    def test_default_transport(self):
        self.setUpClient()
        assert self.client.config['transport'] == 'appenlight_client.transports.requests:HTTPTransport'

    def test_transport_config(self):
        config = {
            'appenlight.transport_config': 'https://api.appenlight.com?threaded=0&timeout=10'}
        self.setUpClient(config)
        superset = self.client.transport.transport_config.items()
        subset = {'url': 'https://api.appenlight.com', 'timeout': 10, 'threaded': 0}
        for i in subset.iteritems():
            assert i in superset


    def test_enabled_client(self):
        self.setUpClient()
        assert self.client.config['enabled'] is True

    def test_disabled_client(self):
        config = {'appenlight': "false"}
        self.setUpClient(config)
        assert self.client.config['enabled'] is False

    def test_disabled_client_no_key(self):
        self.setUpClient({})
        assert self.client.config['enabled'] is False

    def test_server_name(self):
        config = {'appenlight.server_name': "some_name"}
        self.setUpClient(config)
        assert self.client.config['server_name'] == config['appenlight.server_name']

    def test_default_server_name(self):
        self.setUpClient()
        assert self.client.config['server_name'] == socket.getfqdn()

    def test_client_name(self):
        config = {'appenlight.client': "pythonX"}
        self.setUpClient(config)
        assert self.client.config['client'] == config['appenlight.client']

    def test_default_client_name(self):
        self.setUpClient()

        assert self.client.config['client'] == 'python3' if client.PY3 else 'python'

    def test_reraise_exceptions(self):
        config = {'appenlight.reraise_exceptions': "false"}
        self.setUpClient(config)
        assert self.client.config['reraise_exceptions'] is False

    def test_default_reraise_exceptions(self):
        self.setUpClient()
        assert self.client.config['reraise_exceptions'] is True

    def test_default_slow_requests(self):
        self.setUpClient()
        assert self.client.config['slow_requests'] is True

    def test_disabled_slow_requests(self):
        config = {'appenlight.reraise_exceptions': "false"}
        self.setUpClient(config)
        assert self.client.config['reraise_exceptions'] is False

    def test_default_slow_request_time(self):
        self.setUpClient()
        assert self.client.config['slow_request_time'] == datetime.timedelta(seconds=1)

    def test_custom_slow_request_time(self):
        config = {'appenlight.slow_request_time': "2"}
        self.setUpClient(config)
        assert self.client.config['slow_request_time'] == datetime.timedelta(seconds=2)

    def test_too_low_custom_slow_request_time(self):
        config = {'appenlight.slow_request_time': "0.001"}
        self.setUpClient(config)
        assert self.client.config['slow_request_time'] == datetime.timedelta(seconds=0.01)

    def test_default_logging(self):
        self.setUpClient()
        assert self.client.config['logging'] is True

    def test_custom_logging(self):
        config = {'appenlight.logging': "false"}
        self.setUpClient(config)
        assert self.client.config['logging'] is False

    def test_default_logging_on_error(self):
        self.setUpClient()
        assert self.client.config['logging_on_error'] is False

    def test_custom_logging_on_error(self):
        config = {'appenlight.logging_on_error': "true"}
        self.setUpClient(config)
        assert self.client.config['logging_on_error'] is True

    def test_default_report_404(self):
        self.setUpClient()
        assert self.client.config['report_404'] is False

    def test_custom_report_404r(self):
        config = {'appenlight.report_404': "true"}
        self.setUpClient(config)
        assert self.client.config['report_404'] is True

    def test_default_report_errors(self):
        self.setUpClient()
        assert self.client.config['report_errors'] is True

    def test_custom_report_errors(self):
        config = {'appenlight.report_errors': "false"}
        self.setUpClient(config)
        assert self.client.config['report_errors'] is False

    def test_default_buffer_flush_interval(self):
        self.setUpClient()
        assert self.client.config['buffer_flush_interval'] == datetime.timedelta(seconds=5)

    def test_custom_buffer_flush_interval(self):
        config = {'appenlight.buffer_flush_interval': "10"}
        self.setUpClient(config)
        assert self.client.config['buffer_flush_interval'] == datetime.timedelta(seconds=10)

    def test_custom_small_buffer_flush_interval(self):
        config = {'appenlight.buffer_flush_interval': "0"}
        self.setUpClient(config)
        assert self.client.config['buffer_flush_interval'] == datetime.timedelta(seconds=1)

    def test_default_buffer_clear_on_send(self):
        self.setUpClient()
        assert self.client.config['buffer_clear_on_send'] is False

    def test_custom_buffer_clear_on_send(self):
        config = {'appenlight.buffer_clear_on_send': "true"}
        self.setUpClient(config)
        assert self.client.config['buffer_clear_on_send'] is True

    def test_default_force_send(self):
        self.setUpClient()
        assert self.client.config['force_send'] is False

    def test_custom_force_send(self):
        config = {'appenlight.force_send': "1"}
        self.setUpClient(config)
        assert self.client.config['force_send'] is True

    def test_default_request_keys_blacklist(self):
        self.setUpClient()
        assert set(self.client.config['request_keys_blacklist']) == set(['password', 'passwd', 'pwd', 'auth_tkt',
                               'secret',
                               'csrf', 'xsrf', 'auth',
                               'session', 'pass', 'config', 'settings',
                               'environ'])

    def test_custom_request_keys_blacklist(self):
        config = {'appenlight.request_keys_blacklist': "aa,bb,cc"}
        self.setUpClient(config)
        assert set(self.client.config['request_keys_blacklist']) == set(['password', 'passwd', 'pwd', 'auth_tkt',
                               'secret',
                               'csrf', 'xsrf', 'auth', 'session', 'pass',
                               'config', 'settings',
                               'environ', 'aa', 'bb', 'cc'])

    def test_default_environ_keys_whitelist(self):
        self.setUpClient()
        assert self.client.config['environ_keys_whitelist'] == ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME',
                                                                'CONTENT_TYPE', 'HTTP_REFERER']

    def test_custom_environ_keys_whitelist(self):
        config = {'appenlight.environ_keys_whitelist': "aa,bb,cc"}
        self.setUpClient(config)
        assert self.client.config['environ_keys_whitelist'] == ['REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME',
                                                                'CONTENT_TYPE','HTTP_REFERER', 'aa', 'bb', 'cc']

    def test_default_log_namespace_blacklist(self):
        self.setUpClient()
        assert self.client.config['log_namespace_blacklist'] == ['appenlight_client.client',
                                                                 'appenlight_client.transports.requests']

    def test_custom_log_namespace_blacklist(self):
        config = {'appenlight.log_namespace_blacklist': "aa,bb,cc.dd"}
        self.setUpClient(config)
        assert self.client.config['log_namespace_blacklist'] == ['appenlight_client.client',
                                                                 'appenlight_client.transports.requests',
                                                                 'aa', 'bb', 'cc.dd']

    def test_default_filter_callable(self):
        self.setUpClient()
        assert self.client.filter_callable == filter_callable

    def test_bad_filter_callable(self):
        config = {'appenlight.filter_callable': "foo.bar.baz:callable_name"}
        self.setUpClient(config)
        assert self.client.filter_callable == filter_callable

    def test_custom_filter_callable(self):
        config = {'appenlight.filter_callable':
                      "appenlight_client.tests:example_filter_callable"}
        self.setUpClient(config)
        assert self.client.filter_callable.__name__ == example_filter_callable.__name__

    def test_default_logging_handler_present(self):
        self.setUpClient()
        assert len(self.client.log_handlers) > 0

    def test_custom_logging_handler_present(self):
        config = {'appenlight.logging': "false"}
        self.setUpClient(config)
        assert len(self.client.log_handlers) == 0

    def test_default_logging_handler_level(self):
        self.setUpClient()
        assert self.client.log_handlers[0].level == logging.WARNING

    def test_custom_logging_handler_level(self):
        config = {'appenlight.logging.level': "CRITICAL",
                  'appenlight.api_key': '12345'}
        self.setUpClient(config)
        assert self.client.log_handlers[0].level == logging.CRITICAL

    def test_default_timing_config(self):
        self.setUpClient()
        assert self.client.config['timing'] == {}

    def test_timing_config_disable(self):
        config = {'appenlight.timing.dbapi2_psycopg2': 'false',
                  'appenlight.api_key': '12345'}
        self.setUpClient(config)
        assert self.client.config['timing']['dbapi2_psycopg2'] is False

    def test_timing_config_custom(self):
        config = {'appenlight.timing.dbapi2_psycopg2': '5',
                  'appenlight.api_key': '12345'}
        self.setUpClient(config)
        assert self.client.config['timing']['dbapi2_psycopg2'] == 5

    def test_timing_config_mixed(self):
        config = {'appenlight.timing.dbapi2_psycopg2': '5',
                  'appenlight.timing': {'urllib': 11, 'dbapi2_oursql': 6},
                  'appenlight.api_key': '12345'
        }
        self.setUpClient(config)
        assert self.client.config['timing']['dbapi2_psycopg2'] == 5
        assert self.client.config['timing']['dbapi2_oursql'] == 6
        assert self.client.config['timing']['urllib'] == 11


def generate_error():
    pass


class TestClientTransport(BaseTest):

    def test_check_if_deliver_false(self):
        self.setUpClient()
        self.client.last_submit = datetime.datetime.now()
        assert self.client.check_if_deliver() is False

    def test_check_if_deliver_forced(self):
        self.setUpClient()
        self.client.transport.log_queue = ['dummy']
        assert self.client.check_if_deliver(force_send=True) is True

    def test_send_error_failure_queue(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404)
        self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        assert self.client.transport.report_queue == []

    def test_http_transport_failure(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.transport.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        assert result is False

    def test_http_transport_success(self):
        # requires valid key for test
        return True
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://127.0.0.1:6543?threaded=1&timeout=5'})
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.transport.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        assert result is True

    def test_http_transport_timeout(self):
        # requires valid key for test
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://127.0.0.1:6543?threaded=1&timeout=0.0001'})
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.transport.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        assert result is False

    def test_wrong_server_failure(self):
        # requires valid key for test
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5'})
        self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.transport.send(self.client.transport.report_queue, 'reports')
        get_local_storage(local_timing).clear()
        assert result is False

    def test_default_buffer_clear(self):
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5'})
        for x in xrange(10):
            self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        assert len(self.client.transport.report_queue) == 0

    def test_default_buffer_non_empty(self):
        self.setUpClient(
            {'appenlight.api_key': 'XXX',
             'appenlight.transport_config': 'http://foo.bar.baz.com:6543?threaded=1&timeout=5'})
        for x in xrange(255):
            self.client.py_report(TEST_ENVIRON, http_status=404)
        result = self.client.check_if_deliver(force_send=True)
        get_local_storage(local_timing).clear()
        assert len(self.client.transport.report_queue) > 0

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
        assert len(self.client.transport.report_queue) == 0


class TestErrorParsing(BaseTest):

    def test_py_report_404(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=404,
                              start_time=REQ_START_TIME, end_time=REQ_END_TIME)
        subset = PARSED_REPORT_404
        superset = self.client.transport.report_queue[0].items()
        for i in subset.iteritems():
            assert i in superset

    def test_py_report_500_no_traceback(self):
        self.setUpClient()
        self.client.py_report(TEST_ENVIRON, http_status=500,
                              start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        bogus_500_report = copy.deepcopy(PARSED_REPORT_500)
        bogus_500_report['http_status'] = 500
        bogus_500_report['error'] = ''
        del bogus_500_report['traceback']
        bogus_500_report['request_stats'] = {}
        subset = bogus_500_report
        superset = self.client.transport.report_queue[0].items()
        for i in subset.iteritems():
            assert i in superset


    def test_py_report_500_traceback(self):
        self.setUpClient({'appenlight.api_key': 'XXX',
                          'appenlight.report_local_vars': 'false'})
        bogus_report = copy.deepcopy(PARSED_REPORT_500)
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
        self.client.py_report(TEST_ENVIRON, traceback=traceback,
                              http_status=500,
                              start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        line_no = \
            self.client.transport.report_queue[0]['traceback'][0]['line']
        assert int(line_no) > 0
        # set line number to match as this will change over time
        bogus_report['traceback'][0]['line'] = line_no
        subset = bogus_report
        superset = self.client.transport.report_queue[0].items()
        for i in subset.iteritems():
            assert i in superset

    def test_frameinfo(self):
        self.setUpClient(config={'appenlight.report_local_vars': 'true'})
        test = 1
        b = {1: 'a', '2': 2, 'ccc': 'ddd'}
        obj = object()
        e_obj = client.BaseClient({})
        unic = 'grzegżółka'
        a_list = [1, 2, 4, 5, 6, client.BaseClient({}), 'dupa']
        long_val = 'imlong' * 100
        datetest = datetime.datetime.utcnow()
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
        self.client.py_report(TEST_ENVIRON, traceback=traceback,
                              http_status=500)
        assert len(self.client.transport.report_queue[0]['traceback'][0]['vars']) == 9

    def test_frameinfo_dict(self):
        self.setUpClient(config={'appenlight.report_local_vars': 'true'})
        example_dict = {1: u'a', 'foo': u'bar'}
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(
                skip=1,
                show_hidden_frames=True,
                ignore_system_exceptions=True
            )
        self.client.py_report(
            TEST_ENVIRON,
            traceback=traceback,
            http_status=500
        )
        vars = dict(self.client.transport.report_queue[0]['traceback'][0]['vars'])
        assert vars['example_dict'], {'1': u"u'a'", "'foo'": u"u'bar'"}

    def test_cookie_parsing(self):
        self.setUpClient(config={'appenlight.cookie_keys_whitelist': 'country, sessionId, test_group_id, http_referer'})
        proper_values = {u'country': u'US',
             u'sessionId': u'***',
             u'test_group_id': u'5',
             u'http_referer': u'http://localhost:5000/'}
        try:
            raise Exception('Test Exception')
        except:
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
        self.client.py_report(TEST_ENVIRON, traceback=traceback,
                              http_status=500)
        assert self.client.transport.report_queue[0]['request']['COOKIES'] == proper_values


class TestLogs(BaseTest):

    def test_py_log(self):
        self.setUpClient()
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        logger = logging.getLogger('testing')
        msg = 'test entry %s' % random.random()
        logger.critical(msg)
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        fake_log = {'log_level': 'CRITICAL',
                    'namespace': 'testing',
                    'server': 'test-foo',  # this will be different everywhere
                    'request_id': None,
                    'date': '2012-08-13T21:20:37.418.307066',
                    'message': msg}
        # update fields depenand on machine
        self.client.transport.log_queue[0]['date'] = fake_log['date']
        self.client.transport.log_queue[0]['server'] = fake_log['server']
        assert self.client.transport.log_queue[0] == fake_log

    def test_errors_attached_to_logs(self):
        self.setUpClient()
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        logger = logging.getLogger('testing')
        some_num = random.random()
        try:
            raise Exception('This is a test')
        except Exception as e:
            logger.exception('Exception happened %s' % some_num)
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        fake_log = {'log_level': 'ERROR',
                    'namespace': 'testing',
                    'server': 'test-foo',  # this will be different everywhere
                    'request_id': None,
                    'date': '2012-08-13T21:20:37.418.307066',
                    'message': 'Exception happened %s\nTraceback (most recent call last):' % some_num}
        # update fields depenand on machine
        self.client.transport.log_queue[0]['date'] = fake_log['date']
        self.client.transport.log_queue[0]['server'] = fake_log['server']
        assert self.client.transport.log_queue[0]['message'].startswith(fake_log['message'])

    def test_errors_not_attached_to_logs(self):
        self.setUpClient({'appenlight.logging_attach_exc_text': 'false',
                          'appenlight.api_key': 'test_errors_not_attached_to_logs'})
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        logger = logging.getLogger('testing')

        log_msg = 'Exception happened %s' % random.random()
        try:
            raise Exception('This is a test')
        except Exception as e:
            logger.exception(log_msg)
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        fake_log = {'log_level': 'ERROR',
                    'namespace': 'testing',
                    'server': 'test-foo',  # this will be different everywhere
                    'request_id': None,
                    'date': '2012-08-13T21:20:37.418.307066',
                    'message': log_msg}
        # update fields depenand on machine
        self.client.transport.log_queue[0]['date'] = fake_log['date']
        self.client.transport.log_queue[0]['server'] = fake_log['server']
        assert self.client.transport.log_queue[0]['message'] == fake_log['message']

    def test_tags_attached_to_logs(self):
        self.setUpClient()
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        logger = logging.getLogger('testing')
        utcnow = datetime.datetime.utcnow()

        class StrTestObj(object):
            def __repr__(self):
                return "<StrTestObj>"

        logger.critical('test entry',
                        extra={"foobar": "baz",
                               "count": 15,
                               "price": 5.5,
                               "date": utcnow,
                               "obj": StrTestObj(),
                               "dictionary": {"a": "5"}
                        }
        )
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        fake_log = {'log_level': 'CRITICAL',
                    'namespace': 'testing',
                    'server': 'test-foo',  # this will be different everywhere
                    'request_id': None,
                    'date': utcnow.isoformat(),
                    'message': 'test entry',
                    'tags': [("foobar", "baz"),
                             ("count", 15),
                             ("price", 5.5),
                             ("date", utcnow),
                             ("obj", u'<StrTestObj>'),
                             ("dictionary", u"{'a': '5'}")
                    ]}
        # update fields depenand on machine
        self.client.transport.log_queue[0]['server'] = fake_log['server']
        self.client.transport.log_queue[0]['date'] = fake_log['date']
        new_log = self.client.transport.log_queue[0]
        assert new_log['log_level'] == fake_log['log_level']
        assert new_log['namespace'] == fake_log['namespace']
        assert new_log['server'] == fake_log['server']
        assert new_log['request_id'] == fake_log['request_id']
        assert new_log['date'] == fake_log['date']
        assert new_log['message'] == fake_log['message']
        assert set(new_log['tags']) == set(fake_log['tags'])

    def test_primary_key_attached(self):
        self.setUpClient()
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        logger = logging.getLogger('testing')
        logger.critical('test entry',
                        extra={"foobar": "baz",
                               "count": 15,
                               "price": 5.5,
                               'ae_primary_key': 15,
                               "dictionary": {"a": "5"}
                        }
        )
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        new_log = self.client.transport.log_queue[0]
        assert new_log['primary_key'] == '15'

    def test_permanent_log(self):
        self.setUpClient()
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        logger = logging.getLogger('testing')
        logger.critical('test entry',
                        extra={"foobar": "baz",
                               "count": 15,
                               "price": 5.5,
                               'ae_permanent': 1,
                               "dictionary": {"a": "5"}
                        }
        )
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        new_log = self.client.transport.log_queue[0]
        assert new_log['permanent'] == True

    def test_ignore_self_logs(self):
        self.setUpClient()
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler = register_logging(logging.root, self.client.config, cls=handler_cls)
        self.client.py_report(TEST_ENVIRON, http_status=500)
        self.client.py_report(TEST_ENVIRON, start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        records = self.client.log_handlers_get_records()
        self.client.py_log(TEST_ENVIRON, records=records)
        assert len(self.client.transport.log_queue) == 0

    def test_multiple_handlers(self):
        self.setUpClient()
        logger = logging.getLogger('testing')
        logger2 = logging.getLogger('other logger')
        handler_cls = import_from_module('appenlight_client.ext.logging.logger:ThreadLocalHandler')
        handler2 = register_logging(logger2, self.client.config, cls=handler_cls)
        handler2.setLevel(logging.DEBUG)
        self.client.log_handlers.append(handler2)

        logger.critical('test entry',
                        extra={"foobar": "baz",
                               "count": 15,
                               "price": 5.5,
                               'ae_permanent': 1,
                               "dictionary": {"a": "5"}
                        }
        )
        logger.info('this is info')
        logger.debug('debug d')
        logger2.debug('debug d2')
        logger2.info('this is info')
        logger2.warning('this is warning')
        records = self.client.log_handlers_get_records()
        new_log = records[0]
        assert new_log['permanent'] is True
        assert len(records) == 2


class TestSlowReportParsing(BaseTest):

    def test_py_report_slow(self):
        self.setUpClient()
        self.maxDiff = None
        self.client.py_report(TEST_ENVIRON, start_time=REQ_START_TIME,
                              end_time=REQ_END_TIME)
        subset = PARSED_SLOW_REPORT
        superset = self.client.transport.report_queue[0].items()
        for i in subset.iteritems():
            assert i in superset


class TestMakeMiddleware(BaseTest):

    def test_make_middleware(self):
        def app(environ, start_response):
            start_response('200 OK', [('content-type', 'text/html')])
            return ['Hello world!']

        app = make_appenlight_middleware(app, {'appenlight.api_key': '12345'})
        assert isinstance(app, AppenlightWSGIWrapper) is True

    def test_make_middleware_disabled(self):
        def app(environ, start_response):
            start_response('200 OK', [('content-type', 'text/html')])
            return ['Hello world!']

        app = make_appenlight_middleware(app, {'appenlight': 'false'})
        assert isinstance(app, AppenlightWSGIWrapper) is False


class TestCustomTiming(BaseTest):

    def setup_method(self, method):
        self.setUpClient(timing_conf)

    def test_custom_time_trace(self):
        @time_trace(name='foo_func', min_duration=0.1)
        def foo(arg):
            time.sleep(0.2)
            return arg

        foo('a')
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

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
        assert len(result) == 3


class TestTimingHTTPLibs(BaseTest):

    def setup_method(self, method):
        self.setUpClient(timing_conf)

    def test_urllib_URLOpener_open(self):
        import urllib

        opener = urllib.URLopener()
        opener.open("https://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

    def test_urllib_urlretrieve(self):
        import urllib

        urllib.urlretrieve("https://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

    def test_urllib2(self):
        import urllib2

        urllib2.urlopen("https://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

    def test_urllib3(self):
        try:
            import urllib3
        except ImportError:
            return
        http = urllib3.PoolManager()
        http.request('GET', "https://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

    def test_requests(self):
        try:
            import requests
        except ImportError:
            return
        requests.get("https://www.ubuntu.com/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

    def test_httplib(self):
        import httplib

        h2 = httplib.HTTPConnection("www.ubuntu.com")
        h2.request("GET", "/")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1


class TestRedisPY(BaseTest):

    def setup_method(self, method):
        self.setUpClient(timing_conf)

    def test_redis_py_command(self):
        try:
            import redis
        except ImportError:
            return

        client = redis.StrictRedis()
        client.setex('testval', 10, 'foo')
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1


class TestMemcache(BaseTest):

    def setup_method(self, method):
        self.setUpClient(timing_conf)

    def test_memcache_command(self):
        try:
            import memcache
        except ImportError:
            return
        mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        mc.set("some_key", "Some value")
        value = mc.get("some_key")
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 2


class TestPylibMc(BaseTest):

    def setup_method(self, method):
        self.setUpClient(timing_conf)

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
        assert len(result) == 2


class TestDBApi2Drivers(BaseTest):

    def setup_method(self, method):
        timing_conf['appenlight.timing.dbapi2_sqlite3'] = 0.0000000001
        self.setUpClient(timing_conf)
        self.stmt = '''SELECT 1+2+3 as result'''

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
        assert len(result) == 2

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
        assert int(stats['sql_calls']) == 4

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
        assert len(result) == 2

    def test_psycopg2_context_manager(self):
        try:
            import psycopg2
        except ImportError:
            return
        conn = psycopg2.connect(
            "user=test host=127.0.0.1 dbname=test password=test")
        with conn.cursor() as c:
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, c)
            c.execute(self.stmt)
            c.fetchone()
        conn.close()
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 2


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
        assert len(result) == 2

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
        assert len(result) == 2

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
        assert len(result) == 2

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
        assert len(result) == 2

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
        assert len(result) == 2

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
        assert len(result) == 2


class TestMako(BaseTest):

    def setup_method(self, method):
        self.setUpClient(timing_conf)

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
        xxxxx ${1+foo} yyyyyy
        ''')
        template.render(foo=5)
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1

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
        assert stats['tmpl_calls'] == 3

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
        assert len(result) == 1

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
        assert len(result) == 1


class TestChameleon(BaseTest):

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
        assert len(result) == 1


class TestJinja2(BaseTest):

    def test_render(self):
        try:
            import jinja2
        except ImportError:
            return
        import time

        template = jinja2.Template('''
        {{sleep(0.06)}}
        xxxxx {{1+foo}} yyyyyy
        ''')
        template.render(sleep=time.sleep, foo=5, template='XXXX')
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1


class TestDjangoTemplates(BaseTest):

    # def setup_method(self, method):
    #     self.setUpClient(timing_conf)

    def test_render(self):
        try:
            from django import template
        except ImportError:
            return
        from django.conf import settings

        settings.configure(TEMPLATE_DIRS=("/whatever/templates",))
        import time

        ctx = template.Context()
        ctx.update({'time': lambda: time.sleep(0.06), 'template':'x'})
        template = template.Template('''
        xxxxx {{ time }} yyyyyy
        ''')
        template.render(ctx)
        stats, result = get_local_storage(local_timing).get_thread_stats()
        assert len(result) == 1


class TestWSGI(BaseTest):

    def test_normal_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 0

    def test_normal_request_decorator(self):
        from appenlight_client.client import decorate

        @decorate(appenlight_config={'appenlight.api_key': '12345'})
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 0

    def test_error_request_decorator(self):
        from appenlight_client.client import decorate

        @decorate(appenlight_config={'appenlight.api_key': '12345',
                                     'appenlight.reraise_exceptions': False})
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req = Request.blank('http://localhost/test')
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 1

    def test_error_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 1
        assert app.appenlight_client.transport.report_queue[0]['http_status'] == 500


    def test_not_found_request(self):
        def app(environ, start_response):
            start_response('404 Not Found', [('Content-Type', 'text/html')])
            try:
                raise Exception('something wrong')
            except Exception:
                pass
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['report_404'] = True
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 1
        assert app.appenlight_client.transport.report_queue[0]['http_status'] == 404

    def test_ignored_error_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        req.environ['appenlight.ignore_error'] = 1
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 0

    def test_view_name_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            environ['appenlight.view_name'] = 'foo:app'
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert app.appenlight_client.transport.report_queue[0].get('view_name') == 'foo:app'

    def test_slow_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            time.sleep(1.1)
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 1

    def test_ignored_slow_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            time.sleep(1.1)
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        req.environ['appenlight.ignore_slow'] = 1
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert len(app.appenlight_client.transport.report_queue) == 0

    def test_logging_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            logging.warning('test logging')
            logging.critical('test logging critical')
            return ['Hello World!']

        req = Request.blank('http://localhost/test')
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)

        assert len(app.appenlight_client.transport.log_queue) >= 2

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
        assert stats['main'] > 0
        assert stats['sql'] > 0

    def test_multiple_post_request(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test', POST=[("a", "a"), ("b", "2"), ("b", "1")])
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert {'a': u'a', 'b': [u'2', u'1']} == app.appenlight_client.transport.report_queue[0]['request']['POST']

    def test_tags_support(self):
        now = datetime.datetime.utcnow()
        def app(environ, start_response):
            environ['appenlight.tags']['foo'] = u'bar'
            environ['appenlight.tags']['baz'] = 5
            environ['appenlight.tags']['now'] = now
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test', POST=[("a", "a"), ("b", "2"), ("b", "1")])
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert set([('foo', u'bar'), ('baz', 5), ('now', now)]) == set(app.appenlight_client.transport.report_queue[0]['tags'])

    def test_extra_support(self):
        now = datetime.datetime.utcnow()
        def app(environ, start_response):
            environ['appenlight.extra']['foo'] = u'bar'
            environ['appenlight.extra']['baz'] = 5
            environ['appenlight.extra']['now'] = now
            start_response('200 OK', [('Content-Type', 'text/html')])
            raise Exception('WTF?')
            return ['Hello World!']

        req = Request.blank('http://localhost/test', POST=[("a", "a"), ("b", "2"), ("b", "1")])
        app = make_appenlight_middleware(app, global_config=timing_conf)
        app.appenlight_client.config['reraise_exceptions'] = False
        app.appenlight_client.transport.last_submit = datetime.datetime.now()
        req.get_response(app)
        assert set([('foo', u'bar'), ('baz', 5), ('now', now)]) == set(app.appenlight_client.transport.report_queue[0]['extra'])


class TestCallableName(BaseTest):

    def test_func(self):
        def some_call():
            return 1

        fullyQualifiedName(some_call)
        some_call()
        assert some_call._appenlight_name == 'appenlight_client/tests:some_call'

    def test_newstyle_class(self):
        class Foo(object):
            def test(self):
                return 1

            def __call__(self):
                return 2

        fullyQualifiedName(Foo)
        fullyQualifiedName(Foo.test)
        assert Foo._appenlight_name == 'appenlight_client/tests:Foo'
        assert Foo.test._appenlight_name == 'appenlight_client/tests:Foo.test'

    def test_oldstyle_class(self):
        class Bar():
            def test(self):
                return 1

            def __call__(self):
                return 2

        fullyQualifiedName(Bar)
        fullyQualifiedName(Bar.test)
        assert Bar._appenlight_name == 'appenlight_client/tests:Bar'
        assert Bar.test._appenlight_name == 'appenlight_client/tests:Bar.test'


    def test_stack_parsing(self):
        from operator import itemgetter
        slow_calls = [
            {'count': True, 'end': 1423818165.447647, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818165.447433,
             'statement': 'exists', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818165.447962, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818165.447676,
             'statement': 'get', 'type': 'nosql', 'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818165.448502, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818165.448153,
             'statement': 'expire', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818165.448746, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818165.448527,
             'statement': 'expire', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818165.454726, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818165.454365,
             'statement': 'expire', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': False, 'end': 1423818165.464405, 'subtype': 'psycopg2',
             'min_duration': 0.1, 'start': 1423818165.464372,
             'statement': 'fetchall', 'type': 'sql',
             'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818165.755851,
             'parameters': 'http://ubuntu.com', 'min_duration': 3,
             'start': 1423818165.487422, 'statement': 'requests.request',
             'type': 'remote', 'ignore_in': frozenset(['remote', 'nosql'])},
            {'count': True, 'end': 1423818167.419324, 'parameters': '',
             'subtype': 'user_defined', 'min_duration': 0.1,
             'start': 1423818165.756119, 'statement': 'foo_func',
             'type': 'custom', 'ignore_in': set([])},
            {'count': True, 'end': 1423818166.577326,
             'parameters': 'http://ubuntu.com/nested', 'min_duration': 3,
             'start': 1423818166.277095, 'statement': 'requests.request',
             'type': 'remote', 'ignore_in': frozenset(['remote', 'nosql'])},
            {'count': True, 'end': 1423818167.419318, 'parameters': '',
             'subtype': 'user_defined', 'min_duration': 0.1,
             'start': 1423818166.577698, 'statement': 'bar_func',
             'type': 'custom', 'ignore_in': set([])},
            {'count': True, 'end': 1423818167.419286, 'parameters': '',
             'subtype': 'user_defined', 'min_duration': 0.1,
             'start': 1423818167.098667, 'statement': 'baz_func',
             'type': 'custom', 'ignore_in': set([])},
            {'count': True, 'end': 1423818167.419649, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818167.419642,
             'statement': 'set', 'type': 'nosql', 'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818167.419667, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818167.419662,
             'statement': 'expire', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818167.420036, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818167.420032,
             'statement': 'set', 'type': 'nosql', 'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818167.42005, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818167.420047,
             'statement': 'expire', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818167.420323, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818167.42032, 'statement': 'set',
             'type': 'nosql', 'ignore_in': frozenset([])},
            {'count': True, 'end': 1423818167.420332, 'subtype': 'redispy',
             'min_duration': 0.1, 'start': 1423818167.420329,
             'statement': 'expire', 'type': 'nosql',
             'ignore_in': frozenset([])},
            {'count': False, 'end': 1423818167.448087, 'subtype': 'psycopg2',
             'min_duration': 0.1, 'start': 1423818167.448086,
             'statement': 'fetchall', 'type': 'sql',
             'ignore_in': frozenset([])},
            {'count': False, 'end': 1423818167.448974, 'subtype': 'psycopg2',
             'min_duration': 0.1, 'start': 1423818167.448735,
             'statement': 'ROLLBACK', 'type': 'sql',
             'ignore_in': frozenset([])}]

        storage = get_local_storage(local_timing)

        for row in storage.get_stack(slow_calls):
            if row.get('parameters') == 'https://ubuntu.com/nested':
                assert row['parents'] == ['custom']
            elif row['statement'] == 'bar_func':
                assert row['parents'] == ['custom']



if __name__ == '__main__':
    pass
