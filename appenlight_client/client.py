# -*- coding: utf-8 -*-
"""
 Copyright (c) 2010, Webreactor - Marcin Lulek <info@webreactor.eu>
 All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
 DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from __future__ import with_statement
import sys

# are we running python 3.x ?
PY3 = sys.version_info[0] == 3

import datetime
import logging
import threading
import time
import socket
import uuid
import os
from functools import wraps
from appenlight_client import __version__, __protocol_version__
from appenlight_client.utils import asbool, aslist, import_from_module
from webob import Request

if PY3:
    import configparser
else:
    import ConfigParser

DATE_FRMT = '%Y-%m-%dT%H:%M:%S'
LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

log = logging.getLogger(__name__)


class Client(object):
    __version__ = __version__
    __protocol_version__ = __protocol_version__

    def __init__(self, config=None, register_timing=True):
        """
        at minimum client expects following keys to be present::

            appenlight.api_key = YOUR_API_KEY

        """
        self.config = {}
        # general options
        self.config['enabled'] = asbool(config.get('appenlight', True))
        self.config['server_name'] = config.get('appenlight.server_name') \
            or socket.getfqdn()
        if PY3:
            default_client = 'python3'
        else:
            default_client = 'python'
        self.config['client'] = config.get('appenlight.client', default_client)
        self.config['api_key'] = config.get('appenlight.api_key')
        if not self.config['api_key']:
            self.config['enabled'] = False
            logging.warning("Disabling appenlight client, no api key")
        self.config['transport'] = config.get('appenlight.transport',
                                              'appenlight_client.transports.requests:HTTPTransport')

        self.config['transport_config'] = config.get('appenlight.transport_config', 'https://api.appenlight.com?threaded=1&timeout=5')
        self.config['reraise_exceptions'] = asbool(
            config.get('appenlight.reraise_exceptions', True))
        self.config['slow_requests'] = asbool(
            config.get('appenlight.slow_requests', True))
        self.config['slow_request_time'] = float(
            config.get('appenlight.slow_request_time', 1))
        if self.config['slow_request_time'] < 0.01:
            self.config['slow_request_time'] = 0.01
        self.config['slow_request_time'] = datetime.timedelta(
            seconds=self.config['slow_request_time'])
        self.config['logging'] = asbool(config.get('appenlight.logging', True))
        self.config['logging_on_error'] = asbool(
            config.get('appenlight.logging_on_error', False))
        self.config['report_404'] = asbool(config.get('appenlight.report_404',
                                                      False))
        self.config['report_local_vars'] = asbool(
            config.get('appenlight.report_local_vars', False))
        self.config['report_errors'] = asbool(
            config.get('appenlight.report_errors', True))
        self.config['buffer_flush_interval'] = int(
            config.get('appenlight.buffer_flush_interval', 5))
        self.config['buffer_clear_on_send'] = asbool(
            config.get('appenlight.buffer_clear_on_send', False))
        self.config['force_send'] = asbool(config.get('appenlight.force_send',
                                                      False))
        self.config['request_keys_blacklist'] = ['password', 'passwd', 'pwd',
                                                 'auth_tkt', 'secret', 'csrf',
                                                 'session', 'pass', 'config',
                                                 'settings', 'environ', 'xsrf',
                                                 'auth']
        req_blacklist = aslist(config.get('appenlight.request_keys_blacklist',
                                          config.get(
                                              'appenlight.bad_request_keys')),
                               ',')
        self.config['request_keys_blacklist'].extend(
            filter(lambda x: x, req_blacklist)
        )
        if config.get('appenlight.bad_request_keys'):
            log.warning('appenlight.bad_request_keys is deprecated use '
                        'request_keys_blacklist')  # pragma: nocover

        self.config['environ_keys_whitelist'] = [
            'REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE',
            'HTTP_REFERER']
        environ_whitelist = aslist(
            config.get('appenlight.environ_keys_whitelist'), ',')
        self.config['environ_keys_whitelist'].extend(
            filter(lambda x: x, environ_whitelist))
        self.config['log_namespace_blacklist'] = ['appenlight_client.client', 'appenlight_client.transports.requests']

        log_blacklist = aslist(
            config.get('appenlight.log_namespace_blacklist'), ',')
        self.config['log_namespace_blacklist'].extend(filter(
            lambda x: x, log_blacklist))

        self.filter_callable = config.get('appenlight.filter_callable')
        if self.filter_callable:
            try:
                parts = self.filter_callable.split(':')
                _tmp = __import__(parts[0], globals(), locals(),
                                  [parts[1], ], 0)
                self.filter_callable = getattr(_tmp, parts[1])
            except ImportError as e:
                self.filter_callable = self.data_filter
                msg = 'Could not import filter callable, using default, %s' % e
                log.error(msg)
        else:
            self.filter_callable = self.data_filter

        if self.config['buffer_flush_interval'] < 1:
            self.config['buffer_flush_interval'] = 1
        self.config['buffer_flush_interval'] = datetime.timedelta(
            seconds=self.config['buffer_flush_interval'])
        # register logging
        import appenlight_client.logger

        if self.config['logging'] and self.config['enabled']:
            self.log_handler = appenlight_client.logger.register_logging()
            level = LEVELS.get(config.get('appenlight.logging.level',
                                          'WARNING').lower(), logging.WARNING)
            self.log_handler.setLevel(level)

        # register slow call metrics
        if self.config['slow_requests'] and self.config['enabled']:
            self.config['timing'] = config.get('appenlight.timing', {})
            for k, v in config.items():
                if k.startswith('appenlight.timing'):
                    try:
                        self.config['timing'][k[18:]] = float(v)
                    except (TypeError, ValueError) as e:
                        self.config['timing'][k[18:]] = False
            import appenlight_client.timing

            appenlight_client.timing.register_timing(self.config)

        self.hooks = ['hook_pylons']
        self.hooks_blacklist = aslist(config.get('appenlight.hooks_blacklist'),
                                      ',')
        # register hooks
        if self.config['enabled']:
            self.register_hooks()

        self.config['endpoints'] = {
            "reports": '/api/reports',
            "logs": '/api/logs',
            "metrics": '/api/metrics'
        }

        self.report_queue = []
        self.report_queue_lock = threading.RLock()
        self.log_queue = []
        self.log_queue_lock = threading.RLock()
        self.request_stats = {}
        self.request_stats_lock = threading.RLock()
        self.uuid = uuid.uuid4()
        self.last_submit = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=50)
        self.last_request_stats_submit = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=50)

        try:
            parts = self.config['transport'].split(':')
            _tmp = __import__(parts[0], globals(), locals(),
                              [parts[1], ], 0)
            selected_transport = getattr(_tmp, parts[1])
        except ImportError as e:
            from appenlight_client.transports.requests import HTTPTransport as selected_transport

            msg = 'Could not import transport %s, using default, %s' % (self.config['transport'], e)
            log.error(msg)

        self.transport = selected_transport(self.config['transport_config'],
                                            self.config)

    def register_hooks(self):
        for hook in self.hooks:
            if hook in self.hooks_blacklist:
                log.debug('blacklisted %s' % hook)
                continue
            try:
                e_callable = import_from_module(
                    'appenlight_client.hooks.%s:register' % hook)
                if e_callable:
                    e_callable()
            except Exception:
                raise
                log.warning("Couln't attach hook: %s" % hook)

    def check_if_deliver(self, force_send=False):
        delta = datetime.datetime.utcnow() - self.last_submit
        metrics = []
        reports = []
        logs = []
        # should we send
        if delta > self.config['buffer_flush_interval'] or force_send:
            # build data to feed the transport
            with self.report_queue_lock:
                reports = self.report_queue[:250]
                if self.config['buffer_clear_on_send']:
                    self.report_queue = []
                else:
                    self.report_queue = self.report_queue[250:]

            with self.log_queue_lock:
                logs = self.log_queue[:2000]
                if self.config['buffer_clear_on_send']:
                    self.log_queue = []
                else:
                    self.log_queue = self.log_queue[2000:]
            # mark times
            self.last_submit = datetime.datetime.utcnow()

        # metrics we should send every 60s
        delta = datetime.datetime.utcnow() - self.last_request_stats_submit
        if delta >= datetime.timedelta(seconds=60):
            with self.request_stats_lock:
                request_stats = self.request_stats
                self.request_stats = {}
            for k, v in request_stats.iteritems():
                metrics.append({
                    "server": self.config['server_name'],
                    "metrics": v.items(),
                    "timestamp": k.isoformat()
                })
            # mark times
            self.last_request_stats_submit = datetime.datetime.utcnow()

        if reports or logs or metrics:
            self.transport.feed(reports=reports, logs=logs, metrics=metrics)
            return True
        return False

    def data_filter(self, structure, section=None):
        def filter_dict(f_input, dict_method):
            for k in dict_method():
                for bad_key in self.config['request_keys_blacklist']:
                    if bad_key in k.lower():
                        f_input[k] = u'***'

        keys_to_check = ()
        if section in ['error_report', 'slow_report']:
            keys_to_check = (
                structure['report_details'][0]['request'].get('COOKIES'),
                structure['report_details'][0]['request'].get('POST'),
            )
        for source in filter(None, keys_to_check):
            if hasattr(source, 'iterkeys'):
                filter_dict(source, source.iterkeys)
            elif hasattr(source, 'keys'):
                filter_dict(source, source.keys)
                # try to filter local frame vars, to prevent people
                #  leaking as much data as possible when enabling frameinfo
        frameinfo = structure['report_details'][0].get('traceback')
        if frameinfo:
            for f in frameinfo:
                for source in f.get('vars', []):
                    # filter dict likes
                    if hasattr(source[1], 'iterkeys'):
                        filter_dict(source[1], source[1].iterkeys)
                    elif hasattr(source, 'keys'):
                        filter_dict(source[1], source[1].keys)
                    # filter flat values
                    else:
                        for bad_key in self.config['request_keys_blacklist']:
                            if bad_key in source[0].lower():
                                source[1] = u'***'
        return structure

    def py_report(self, environ, traceback=None, message=None, http_status=200,
                  start_time=None, end_time=None, request_stats=None,
                  slow_calls=None):
        if not request_stats:
            request_stats = {}
        report_data, appenlight_info = self.create_report_structure(environ,
                                                                    traceback,
                                                                    server=self.config['server_name'],
                                                                    http_status=http_status,
                                                                    include_params=True)
        report_data = self.filter_callable(report_data, 'error_report')
        url = report_data['report_details'][0]['url']
        if not PY3:
            url = url.decode('utf8', 'ignore')
        report_data['report_details'][0]['request_stats'] = request_stats
        with self.report_queue_lock:
            self.report_queue.append(report_data)
        if traceback:
            try:
                log.warning('%s code: %s @%s' % (http_status,
                                                 report_data.get('error').encode('utf8', 'ignore'),
                                                 url.encode('utf8', 'ignore'),))
                log.error(
                    report_data.get('error', '').encode('utf8', 'ignore'))
                log.error(traceback.plaintext.encode('utf8', 'ignore'))
            except Exception:
                pass
        del traceback
        report_data['report_details'][0]['start_time'] = start_time
        report_data['report_details'][0]['end_time'] = end_time
        report_data['report_details'][0]['request_stats'] = request_stats
        report_data['report_details'][0]['slow_calls'] = []
        if slow_calls:
            for record in slow_calls:
                # we don't need that and json will barf anyways
                # but operate on copy
                r = dict(getattr(record, 'appenlight_data', record))
                r.pop('ignore_in', None)
                r.pop('parents', None)
                r.pop('count', None)
                r.pop('min_duration', None)
                # convert to datetime before json payload gets created
                r['start'] = datetime.datetime.utcfromtimestamp(r['start'])
                r['end'] = datetime.datetime.utcfromtimestamp(r['end'])
                report_data['report_details'][0]['slow_calls'].append(r)
            try:
                log.info('slow request/queries detected: %s' % url.encode('utf8', 'ignore'))
            except Exception:
                pass
        return True

    def py_log(self, environ, records=None, r_uuid=None, created_report=None):
        log_entries = []
        if not records:
            records = self.log_handler.get_records()
            self.log_handler.clear_records()

        if not environ.get('appenlight.force_logs') and \
                (self.config['logging_on_error'] and created_report is None):
            return False

        for record in records:
            if record.name in self.config['log_namespace_blacklist']:
                continue
            if not getattr(record, 'created'):
                time_string = datetime.datetime.utcnow().isoformat()
            else:
                time_string = time.strftime(
                    DATE_FRMT,
                    time.gmtime(record.created)) + ('.%f' % record.msecs)
            try:
                message = record.getMessage()
                log_dict = {'log_level': record.levelname,
                            "namespace": record.name,
                            'server': self.config['server_name'],
                            'date': time_string,
                            'request_id': r_uuid}
                if PY3:
                    log_dict['message'] = '%s' % message
                else:
                    msg = message.encode('utf8') if isinstance(message,
                                                               unicode) else message
                    log_dict['message'] = '%s' % msg
                log_entries.append(log_dict)
            except (TypeError, UnicodeDecodeError, UnicodeEncodeError) as e:
                # handle some weird case where record.getMessage() fails
                log.warning(e)
        with self.log_queue_lock:
            self.log_queue.extend(log_entries)
        log.debug('add %s log entries to queue' % len(records))
        return True

    def save_request_stats(self, stats, view_name=None):
        if not view_name:
            view_name = 'unresolved_view'
        with self.request_stats_lock:
            req_time = datetime.datetime.utcnow().replace(second=0,
                                                          microsecond=0)
            if req_time not in self.request_stats:
                self.request_stats[req_time] = {}
            if view_name not in self.request_stats[req_time]:
                self.request_stats[req_time][view_name] = {'main': 0,
                                                           'sql': 0,
                                                           'nosql': 0,
                                                           'remote': 0,
                                                           'tmpl': 0,
                                                           'unknown': 0,
                                                           'requests': 0,
                                                           'custom': 0,
                                                           'sql_calls': 0,
                                                           'nosql_calls': 0,
                                                           'remote_calls': 0,
                                                           'tmpl_calls': 0,
                                                           'custom_calls': 0}
            self.request_stats[req_time][view_name]['requests'] += 1
            for k, v in stats.iteritems():
                self.request_stats[req_time][view_name][k] += v

    def process_environ(self, environ, traceback=None, include_params=False,
                        http_status=200):
        # form friendly to json encode
        parsed_environ = {}
        appenlight_info = {}
        if 'PATH_INFO' in environ or 'SERVER_NAME' in environ or 'wsgi.url_scheme' in environ:
            # dummy data for Request to work
            if 'wsgi.url_scheme' not in environ:
                environ['wsgi.url_scheme'] = 'http'
                environ['HTTP_HOST'] = ""
            try:
                req = Request(environ)
            except Exception:
                req = None
        else:
            req = None
        for key, value in environ.items():
            if key.startswith('appenlight.') \
                and key not in ('appenlight.client',
                                'appenlight.force_send',
                                'appenlight.log',
                                'appenlight.report',
                                'appenlight.force_logs',
                                'appenlight.post_vars'):
                appenlight_info[key[11:]] = unicode(value)
            else:
                whitelisted = key.startswith('HTTP') or key in self.config[
                    'environ_keys_whitelist']
                if http_status not in [404, '404'] and whitelisted:
                    try:
                        if isinstance(value, str):
                            if PY3:
                                parsed_environ[key] = value
                            else:
                                parsed_environ[key] = value.decode('utf8')
                        else:
                            parsed_environ[key] = unicode(value)
                    except Exception:
                        pass
                        # provide better details for 500's
        try:
            parsed_environ['HTTP_METHOD'] = req.method
        except Exception:
            pass
        if include_params and req:
            try:
                parsed_environ['COOKIES'] = dict(req.cookies)
            except Exception:
                parsed_environ['COOKIES'] = {}
            try:
                parsed_environ['GET'] = dict([(k, req.GET.getall(k),) for k in req.GET])
            except Exception:
                parsed_environ['GET'] = {}
            try:
                # handle werkzeug and django
                wz_post_vars = req.environ.get('appenlight.post_vars', None)
                if wz_post_vars is not None:
                    parsed_environ['POST'] = dict(wz_post_vars)
                else:
                    # webob uses _parsed_post_vars - so this will not fail
                    parsed_environ['POST'] = dict([(k, req.POST.getall(k))
                                                   for k in req.POST])
            except Exception:
                parsed_environ['POST'] = {}

        # figure out real ip
        if environ.get("HTTP_X_FORWARDED_FOR"):
            remote_addr = environ.get("HTTP_X_FORWARDED_FOR").split(',')[
                0].strip()
        else:
            remote_addr = (
                environ.get("HTTP_X_REAL_IP") or environ.get('REMOTE_ADDR'))
        parsed_environ['HTTP_USER_AGENT'] = environ.get("HTTP_USER_AGENT", '')
        parsed_environ['REMOTE_ADDR'] = remote_addr
        try:
            username = appenlight_info.get('username', environ.get('REMOTE_USER', u''))
            appenlight_info['username'] = u'%s' % username
        except (UnicodeEncodeError, UnicodeDecodeError):
            appenlight_info['username'] = "undecodable"
        try:
            appenlight_info['URL'] = req.url
        except (UnicodeEncodeError, UnicodeDecodeError):
            appenlight_info['URL'] = '/invalid-encoded-url'
        except Exception:
            appenlight_info['URL'] = 'unknown'
        return parsed_environ, appenlight_info

    def create_report_structure(self, environ, traceback=None, message=None,
                                http_status=200, server='unknown server',
                                include_params=False):
        if environ is None:
            environ = {}
        (parsed_environ, appenlight_info) = self.process_environ(
            environ,
            traceback,
            include_params,
            http_status)
        report_data = {'client': 'appenlight-python', 'language':'python', 'report_details': []}
        report_data['error'] = ''
        detail_entry = {}
        if traceback:
            exception_text = traceback.exception
            report_data['error'] = exception_text
            local_vars = (self.config['report_local_vars'] or
                          environ.get('appenlight.report_local_vars'))
            detail_entry['traceback'] = traceback.frameinfo(
                include_vars=local_vars)

        report_data['http_status'] = http_status
        if http_status == 404:
            report_data['error'] = '404 Not Found'
        report_data['priority'] = 5
        report_data['server'] = (server or
                                 environ.get('SERVER_NAME', 'unknown server'))
        detail_entry['request'] = parsed_environ
        # fill in all other required info
        detail_entry['ip'] = parsed_environ.get('REMOTE_ADDR', u'')
        detail_entry['user_agent'] = parsed_environ['HTTP_USER_AGENT']
        detail_entry['username'] = appenlight_info.pop('username')
        detail_entry['url'] = appenlight_info.pop('URL', 'unknown')
        if 'request_id' in appenlight_info:
            detail_entry['request_id'] = appenlight_info.pop('request_id',
                                                             None)
        detail_entry['message'] = message or appenlight_info.get('message',
                                                                 u'')
        # conserve bandwidth pop keys that we dont need in request details
        exclude_keys = ('HTTP_USER_AGENT', 'REMOTE_ADDR', 'HTTP_COOKIE',
                        'appenlight.client')
        for k in exclude_keys:
            detail_entry['request'].pop(k, None)
        report_data['report_details'].append(detail_entry)
        report_data.update(appenlight_info)
        del traceback
        return report_data, appenlight_info


def get_config(config=None, path_to_config=None, section_name='appenlight'):
    if not config and not path_to_config:
        path_to_config = os.environ.get('APPENLIGHT_INI')
        if not path_to_config:
            path_to_config = os.environ.get('ERRORMATOR_INI')
    if config is None:
        config = {}
    api_key = os.environ.get('APPENLIGHT_KEY')
    if not api_key:
        api_key = os.environ.get('ERRORMATOR_KEY')
    if path_to_config:
        file_config = {}
        if not os.path.exists(path_to_config):
            logging.warning("Couldn't locate %s " % path_to_config)
            return config
        with open(path_to_config) as f:
            parser = ConfigParser.SafeConfigParser()
            parser.readfp(f)
            try:
                file_config = dict(parser.items(section_name))
            except ConfigParser.NoSectionError:
                logging.warning('No section name '
                                'called %s in file' % section_name)
            config.update(file_config)
            if not config.get('api_key') and api_key:
                config['appenlight.api_key'] = api_key
    if not config.get('api_key') and api_key:
        config['appenlight.api_key'] = api_key
    if not config.get('appenlight.api_key'):
        logging.warning(
            "appenlight.api_key is missing from the config, "
            "something went wrong." "hint: APPENLIGHT_INI/APPENLIGHT_KEY "
            "config variable is missing from environment or api key was "
            "not passed in app global config")
    return config or {}


def decorate(appenlight_config=None):
    def app_decorator(app):
        @wraps(app)
        def app_wrapper(*args, **kwargs):
            return make_appenlight_middleware(app, appenlight_config)

        return app_wrapper()

    return app_decorator


# TODO: refactor this to share the code
def make_appenlight_middleware(app, global_config=None, **kw):
    if global_config:
        config = global_config.copy()
    else:
        config = {}
    config.update(kw)
    ini_path = os.environ.get('APPENLIGHT_INI',
                              config.get('appenlight.config_path'))
    if not ini_path:
        ini_path = os.environ.get('ERRORMATOR_INI',
                                  config.get('errormator.config_path'))
    config = get_config(config=config, path_to_config=ini_path)
    client = Client(config)
    from appenlight_client.wsgi import AppenlightWSGIWrapper

    if client.config['enabled']:
        app = AppenlightWSGIWrapper(app, client)
    return app
