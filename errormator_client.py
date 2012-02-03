# -*- coding: utf-8 -*-

# Copyright (c) 2010, Webreactor - Marcin Lulek <info@webreactor.eu>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import cStringIO
import datetime
import gzip
import logging
import urllib
import urllib2
import socket
import sys
import threading
import time
from logging.handlers import MemoryHandler, BufferingHandler
from webob import Request

import json
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()      
        return json.JSONEncoder.default(self, obj)

from paste import request as paste_req
from paste.util.converters import asbool

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

log = logging.getLogger(__name__)
# used for slow query GATHERING/ - to be picked up by threaded logger
log_slow = logging.getLogger('errormator_client.slow')
log_slow.setLevel(logging.DEBUG)
# used to log errors and flushing them out to api 
log_errors = logging.getLogger('errormator_client.error')
log_errors.setLevel(logging.DEBUG)
# used to log slow reports and flushing them out to api
log_slow_reports = logging.getLogger('errormator_client.slow_report')
log_slow_reports.setLevel(logging.DEBUG)

DATE_FRMT = '%Y-%m-%dT%H:%M:%S.%f'

def gzipcompress(bytestr):
    stream = cStringIO.StringIO()
    gzstream = gzip.GzipFile(fileobj=stream, compresslevel=1, mode='wb')
    try:
        try:
            gzstream.write(bytestr)
        finally:
            gzstream.close()
        return stream.getvalue()
    finally:
        stream.close()


#lets try to find fqdn
fqdn = socket.getfqdn()

def sqlalchemy_07_listener(delta):
    from sqlalchemy import event
    from sqlalchemy.engine.base import Engine
    
    @event.listens_for(Engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, stmt, params, context, execmany):
        setattr(conn, 'err_query_start', datetime.datetime.utcnow())

    @event.listens_for(Engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, stmt, params, context, execmany):
        td = datetime.datetime.utcnow() - conn.err_query_start
        if td >= delta:
            duration = float('%s.%s' % (
                        (td.seconds + td.days * 24 * 3600) * 10 ** 6 / 10 ** 6,
                             td.microseconds)
                             )
            query_info = {'type':'sqlalchemy',
                          'timestamp':conn.err_query_start.isoformat(),
                          'duration': duration,
                          'statement': stmt,
                          'parameters': params
                    }
            log_slow.debug('slow query detected',
                             extra={'errormator_data':query_info}
                              )
        delattr(conn, 'err_query_start')

class ErrormatorException(Exception):

    @property
    def message(self):
        return self._message

    @message.setter
    def message_set(self, message):
        self._message = message

    def __str__(self):
        return repr(self.args)

#utils

def send_request(data, request_url, timeout=30,
                 exception_on_failure=False,
                 gzip=False):
    try:
        req = urllib2.Request(request_url,
                              json.dumps(data, cls=DateTimeEncoder),
                              headers={'Content-Type': 'application/json'})
        #req.headers['Content-Encoding'] = 'gzip'
        try:
            conn = urllib2.urlopen(req, timeout=timeout)
            conn.close()
            return True
        except TypeError as e:
            conn = urllib2.urlopen(req)
        if conn.getcode() != 200:
            message = 'ERRORMATOR: response code: %s' % conn.getcode()
            log.error(message)
            if exception_on_failure:
                raise ErrormatorException(message)
    except IOError as e:
        message = 'ERRORMATOR: problem: %s' % e
        log.error(message)
        if exception_on_failure:
            raise ErrormatorException(message)

def process_environ(environ, traceback=False):
    parsed_request = {}
    additional_info = {}
    for key, value in environ.items():
        if key.startswith('errormator.'):
            additional_info[key[11:]] = unicode(value)
        try:
            if isinstance(value, str):
                parsed_request[key] = value.decode('utf8')
            else:
                parsed_request[key] = unicode(value)
        except:
            # this CAN go wrong
            pass
    if traceback:
        # only do this if there was an error
        # reparse with webob to get all the info we want
        req = Request(environ)
        parsed_request['ERRORMATOR_COOKIES'] = dict(req.cookies)
        parsed_request['ERRORMATOR_GET'] = dict([(k, req.GET.getall(k)) for k in req.GET])
        parsed_request['ERRORMATOR_POST'] = dict([(k, req.POST.getall(k)) for k in req.POST])
    if environ.get("HTTP_X_REAL_IP"):
        remote_addr = environ.get("HTTP_X_REAL_IP")
    elif environ.get("HTTP_X_FORWARDED_FOR"):
        remote_addr = environ.get("HTTP_X_FORWARDED_FOR")\
                .split(',')[0].strip()
    else:
        remote_addr = environ.get('REMOTE_ADDR')
    return parsed_request, remote_addr, additional_info

def create_report_structure(environ, traceback=None, message=None,
                     http_status=200, server='unknown server'):
    (parsed_request, remote_addr, additional_info) = \
            process_environ(environ, traceback)
    parsed_data = {'report_details': []}
    parsed_data['http_status'] = 500 if traceback else http_status
    parsed_data['priority'] = 5
    parsed_data['server'] = (server or
                environ.get('SERVER_NAME', 'unknown server'))
    detail_entry = {}
    if traceback:
        detail_entry['request'] = parsed_request
        #conserve bandwidth
        detail_entry['request'].pop('HTTP_USER_AGENT', None)
        detail_entry['request'].pop('REMOTE_ADDR', None)
        detail_entry['request'].pop('HTTP_COOKIE', None)
        detail_entry['request'].pop('webob._parsed_cookies', None)
        detail_entry['request'].pop('webob._parsed_post_vars', None)
        detail_entry['request'].pop('webob._parsed_query_vars', None)
        
        
    detail_entry['ip'] = remote_addr
    detail_entry['user_agent'] = environ.get('HTTP_USER_AGENT')
    detail_entry['username'] = environ.get('REMOTE_USER', u'')
    detail_entry['url'] = paste_req.construct_url(environ)
    message = message or additional_info.get('message', u'')
    detail_entry['message'] = message
    parsed_data['report_details'].append(detail_entry)
    return parsed_data, additional_info



class ErrormatorLogHandler(MemoryHandler):
    def __init__(self, capacity=50, async=True, api_key=None, server_url=None,
                 server_name=None, timeout=30, buffer_flush_time=60):
        """
        Initialize the handler with the buffer size, the level at which
        flushing should occur and an optional target.
        """
        BufferingHandler.__init__(self, capacity)
        self.capacity = capacity
        self.async = asbool(async)
        self.api_key = api_key
        self.server_url = server_url
        self.timeout = timeout
        self.server = server_name or fqdn
        self.buffer_flush_time = buffer_flush_time
        self.last_flush_time = datetime.datetime.now()

    def shouldFlush(self, record):
        """
        Check for buffer full or a record at the flushLevel or higher.
        """
        tdelta = datetime.datetime.now() - self.last_flush_time
        return (len(self.buffer) >= self.capacity or 
                tdelta.seconds >= self.buffer_flush_time)
    
    def emit(self, record):
        #skip reports from errormator itself
        if record.name.startswith('errormator_client'):
            return
        MemoryHandler.emit(self, record)
        
    def flush(self):
        """
        For a ErrormatorLog, flushing means just sending the buffered
        records to the listerner, if there is one.
        """
        entries = []
        # if service basic data is not supplied just clear the buffer
        if self.api_key and self.server_url: 
            for record in self.buffer:
                if not getattr(record, 'created'):
                    time_string = datetime.datetime.utcnow().isoformat()
                else:
                    time_string = time.strftime(DATE_FRMT,
                                    time.gmtime(record.created)) % record.msecs 
                try:
                    entries.append(
                            {'log_level':record.levelname,
                            'message':'%s %s' % (record.name, record.getMessage().encode('utf8'),),
                            'server': self.server,
                            'date':time_string
                            })
                except (TypeError, UnicodeDecodeError, UnicodeEncodeError), e :
                    #handle some weird case where record.getMessage() fails
                    log.warning(e)
            
            remote_call = RemoteCall(entries)
            if self.async:
                remote_call_async = AsyncRemoteCall(self.api_key,
                                                    self.server_url,
                                                    remote_call,
                                                    self.timeout,
                                                    endpoint='/api/logs')
                remote_call_async.start()
            else:
                remote_call.submit(self.api_key, self.server_url,
                        timeout=self.timeout, endpoint='/api/logs')        
        self.buffer = []
        self.last_flush_time = datetime.datetime.now()

class ErrormatorReportHandler(MemoryHandler):
    def __init__(self, capacity=5, async=True, api_key=None, server_url=None,
                 server_name=None, timeout=30, buffer_flush_time=60, endpoint=None):
        """
        Initialize the handler with the buffer size, the level at which
        flushing should occur and an optional target.
        """
        BufferingHandler.__init__(self, capacity)
        self.capacity = capacity
        self.async = asbool(async)
        self.api_key = api_key
        self.server_url = server_url
        self.timeout = timeout
        self.server = server_name or fqdn
        self.buffer_flush_time = buffer_flush_time
        self.last_flush_time = datetime.datetime.now()
        self.endpoint = endpoint
        if endpoint == '/api/slow_reports':
            self.allow_emit = 'errormator_client.slow_report'
        elif endpoint == '/api/reports':
            self.allow_emit = 'errormator_client.error'

    def shouldFlush(self, record):
        """
        Check for buffer full or a record at the flushLevel or higher.
        """
        tdelta = datetime.datetime.now() - self.last_flush_time
        return (len(self.buffer) >= self.capacity or 
                tdelta.seconds >= self.buffer_flush_time)
    
    def emit(self, record):
        if record.name == self.allow_emit:
            MemoryHandler.emit(self, record)
        
    def flush(self):
        """
        For a ErrormatorLog, flushing means just sending the buffered
        records to the listerner, if there is one.
        """
        entries = []
        # if service basic data is not supplied just clear the buffer
        if self.api_key and self.server_url and self.endpoint: 
            for record in self.buffer:
                entries.append(record.errormator_data)            
            remote_call = RemoteCall(entries)
            if self.async:
                remote_call_async = AsyncRemoteCall(self.api_key,
                                                    self.server_url,
                                                    remote_call,
                                                    self.timeout,
                                                    endpoint=self.endpoint)
                remote_call_async.start()
            else:
                remote_call.submit(self.api_key, self.server_url,
                        timeout=self.timeout, endpoint=self.endpoint)
        self.buffer = []
        self.last_flush_time = datetime.datetime.now()


class RemoteCall(object):
    """ Handled actual communication of data to the server """
    __protocol_version__ = '0.2'

    def __init__(self, payload={}):
        self.payload = payload

    def submit(self, api_key, server_url,
               endpoint=None,
               errormator_client='python',
               exception_on_failure=False,
               timeout=30,
               gzip=False):
        if not endpoint:
            raise ErrormatorException('No endpoint specified')
        GET_vars = urllib.urlencode(
                        {'api_key': api_key,
                        'protocol_version': self.__protocol_version__})
        server_url = '%s%s?%s' % (server_url, endpoint, GET_vars,)
        if send_request(self.payload, server_url, timeout=timeout,
                        exception_on_failure=exception_on_failure):
            message = '%s entries sent: %s' % (endpoint, len(self.payload),)
            log.info(message)

class AsyncRemoteCall(threading.Thread):
    def __init__(self, api_key, server_url, callable, timeout, endpoint):
        super(AsyncRemoteCall, self).__init__()
        self.callable = callable
        self.api_key = api_key
        self.server_url = server_url
        self.timeout = timeout
        self.endpoint = endpoint

    def run(self):
        self.callable.submit(self.api_key, self.server_url,
                             timeout=self.timeout, endpoint=self.endpoint)

# taken from pyramid_debugtoolbar - special kudos for raydeo and pyramid team ;)
# https://github.com/Pylons/pyramid_debugtoolbar
class ThreadTrackingHandler(logging.Handler):
    def __init__(self):
        if threading is None:
            raise NotImplementedError(
                "threading module is not available, "
                "the logging panel cannot be used without it")
        logging.Handler.__init__(self)
        self.records = {} # a dictionary that maps threads to log records

    def emit(self, record):
        #append reports from errormator slow queries
        if record.name in ('errormator_client.slow',):
            self.get_records().append(record)

    def get_records(self, thread=None):
        """
        Returns a list of records for the provided thread, of if none is
        provided, returns a list for the current thread.
        """
        if thread is None:
            thread = threading.currentThread()
        if thread not in self.records:
            self.records[thread] = []
        return self.records[thread]

    def clear_records(self, thread=None):
        if thread is None:
            thread = threading.currentThread()
        if thread in self.records:
            del self.records[thread]


# the code below is shamelessly ripped (and slightly altered)
# from the flickzeug package

# Copyright (c) 2009 by the Flickzeug Team, see AUTHORS for more details.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * The names of the contributors may not be used to endorse or
#      promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
    flickzeug.debug.tbtools
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module provides various traceback related utility functions.

    :copyright: (c) 2009 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD.
"""
import re
import os
import inspect
import traceback
import codecs


_coding_re = re.compile(r'coding[:=]\s*([-\w.]+)')
_line_re = re.compile(r'^(.*?)$(?m)')
_funcdef_re = re.compile(r'^(\s*def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)')
UTF8_COOKIE = '\xef\xbb\xbf'

system_exceptions = (SystemExit, KeyboardInterrupt)
try:
    system_exceptions += (GeneratorExit,)
except NameError:
    pass


class _Missing(object):

    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_missing = _Missing()


class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.

    .. versionchanged:: 0.6
       the `writeable` attribute and parameter was deprecated.  If a
       cached property is writeable or not has to be documented now.
       For performance reasons the implementation does not honor the
       writeable setting and will always make the property writeable.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor.  non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dict__.
    # this allows us to completely get rid of the access function call
    # overhead.  If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func, name=None, doc=None, writeable=False):
        if writeable:
            from warnings import warn
            warn(DeprecationWarning('the writeable argument to the '
                                    'cached property is a noop since 0.6 '
                                    'because the property is writeable '
                                    'by default for performance reasons'))

        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def get_current_traceback(ignore_system_exceptions=False,
                          show_hidden_frames=False, skip=0):
    """Get the current exception info as `Traceback` object.  Per default
    calling this method will reraise system exceptions such as generator exit,
    system exit or others.  This behavior can be disabled by passing `False`
    to the function as first parameter.
    """
    exc_type, exc_value, tb = sys.exc_info()
    if ignore_system_exceptions and exc_type in system_exceptions:
        raise
    for x in xrange(skip):
        if tb.tb_next is None:
            break
        tb = tb.tb_next
    tb = Traceback(exc_type, exc_value, tb)
    if not show_hidden_frames:
        tb.filter_hidden_frames()
    return tb


class Line(object):
    """Helper for the source renderer."""
    __slots__ = ('lineno', 'code', 'in_frame', 'current')

    def __init__(self, lineno, code):
        self.lineno = lineno
        self.code = code
        self.in_frame = False
        self.current = False

    def classes(self):
        rv = ['line']
        if self.in_frame:
            rv.append('in-frame')
        if self.current:
            rv.append('current')
        return rv
    classes = property(classes)


class Traceback(object):
    """Wraps a traceback."""

    def __init__(self, exc_type, exc_value, tb):
        self.exc_type = exc_type
        self.exc_value = exc_value
        if not isinstance(exc_type, str):
            exception_type = exc_type.__name__
            if exc_type.__module__ not in ('__builtin__', 'exceptions'):
                exception_type = exc_type.__module__ + '.' + exception_type
        else:
            exception_type = exc_type
        self.exception_type = exception_type

        # we only add frames to the list that are not hidden.  This follows
        # the the magic variables as defined by paste.exceptions.collector
        self.frames = []
        while tb:
            self.frames.append(Frame(exc_type, exc_value, tb))
            tb = tb.tb_next

    def filter_hidden_frames(self):
        """Remove the frames according to the paste spec."""
        new_frames = []
        hidden = False
        for frame in self.frames:
            hide = frame.hide
            if hide in ('before', 'before_and_this'):
                new_frames = []
                hidden = False
                if hide == 'before_and_this':
                    continue
            elif hide in ('reset', 'reset_and_this'):
                hidden = False
                if hide == 'reset_and_this':
                    continue
            elif hide in ('after', 'after_and_this'):
                hidden = True
                if hide == 'after_and_this':
                    continue
            elif hide or hidden:
                continue
            new_frames.append(frame)

        # if the last frame is missing something went terrible wrong :(
        if self.frames[-1] in new_frames:
            self.frames[:] = new_frames

    @property
    def is_syntax_error(self):
        """Is it a syntax error?"""
        return isinstance(self.exc_value, SyntaxError)

    @property
    def exception(self):
        """String representation of the exception."""
        buf = traceback.format_exception_only(self.exc_type, self.exc_value)
        return ''.join(buf).strip().decode('utf-8', 'replace')

    def log(self, logfile=None):
        """Log the ASCII traceback into a file object."""
        if logfile is None:
            logfile = sys.stderr
        tb = self.plaintext.encode('utf-8', 'replace').rstrip() + '\n'
        logfile.write(tb)

    @cached_property
    def plaintext(self):
        result = ['Traceback (most recent call last):']
        for frame in self.frames:
            result.append('File "%s", line %s, in %s' % 
                    (frame.filename, frame.lineno, frame.function_name,))
            result.append('    %s' % frame.current_line.strip())
        result.append('%s' % self.exception)
        return '\n'.join(result)

    id = property(lambda x: id(x))


class Frame(object):
    """A single frame in a traceback."""

    def __init__(self, exc_type, exc_value, tb):
        self.lineno = tb.tb_lineno
        self.function_name = tb.tb_frame.f_code.co_name
        self.locals = tb.tb_frame.f_locals
        self.globals = tb.tb_frame.f_globals

        fn = inspect.getsourcefile(tb) or inspect.getfile(tb)
        if fn[-4:] in ('.pyo', '.pyc'):
            fn = fn[:-1]
        # if it's a file on the file system resolve the real filename.
        if os.path.isfile(fn):
            fn = os.path.realpath(fn)
        self.filename = fn
        self.module = self.globals.get('__name__')
        self.loader = self.globals.get('__loader__')
        self.code = tb.tb_frame.f_code

        # support for paste's traceback extensions
        self.hide = self.locals.get('__traceback_hide__', False)
        info = self.locals.get('__traceback_info__')
        if info is not None:
            try:
                info = unicode(info)
            except UnicodeError:
                info = str(info).decode('utf-8', 'replace')
        self.info = info

    def eval(self, code, mode='single'):
        """Evaluate code in the context of the frame."""
        if isinstance(code, basestring):
            if isinstance(code, unicode):
                code = UTF8_COOKIE + code.encode('utf-8')
            code = compile(code, '<interactive>', mode)
        if mode != 'exec':
            return eval(code, self.globals, self.locals)
        exec code in self.globals, self.locals

    @cached_property
    def sourcelines(self):
        """The sourcecode of the file as list of unicode strings."""
        # get sourcecode from loader or file
        source = None
        if self.loader is not None:
            try:
                if hasattr(self.loader, 'get_source'):
                    source = self.loader.get_source(self.module)
                elif hasattr(self.loader, 'get_source_by_code'):
                    source = self.loader.get_source_by_code(self.code)
            except:
                # we munch the exception so that we don't cause troubles
                # if the loader is broken.
                pass

        if source is None:
            try:
                f = file(self.filename)
            except IOError:
                return []
            try:
                source = f.read()
            finally:
                f.close()

        # already unicode?  return right away
        if isinstance(source, unicode):
            return source.splitlines()

        # yes. it should be ascii, but we don't want to reject too many
        # characters in the debugger if something breaks
        charset = 'utf-8'
        if source.startswith(UTF8_COOKIE):
            source = source[3:]
        else:
            for idx, match in enumerate(_line_re.finditer(source)):
                match = _line_re.search(match.group())
                if match is not None:
                    charset = match.group(1)
                    break
                if idx > 1:
                    break

        # on broken cookies we fall back to utf-8 too
        try:
            codecs.lookup(charset)
        except LookupError:
            charset = 'utf-8'

        return source.decode(charset, 'replace').splitlines()

    @property
    def current_line(self):
        try:
            return self.sourcelines[self.lineno - 1]
        except IndexError:
            return u''

    id = property(lambda x: id(x))


class TracebackCatcher(object):
    """Enables exception catching for an application

    TracebackCatcher enables a developer to report exceptions when they
    occur in an application in an extensible fashion. When an exception
    occurs, a :class:`flickzeug.tbtools.Traceback` object is created,
    then passed along with the environ into the callable specified with
    the callback parameter.

    A plain 500 Server Error is returned when an exception occurs.

    :param callback: the function to call with the traceback when an
                     exception occurs
    :param catch_callback: boolean indicating whether exceptions thrown
                           while calling the callback should be caught

    """
    def __init__(self, app, callback, catch_callback=True):
        self.app = app
        self.callback = callback
        self.catch_callback = catch_callback

    def __call__(self, environ, start_response):
        """Run the application and conserve the traceback frames."""
        app_iter = None
        try:
            app_iter = self.app(environ, start_response)
            for item in app_iter:
                yield item
            if hasattr(app_iter, 'close'):
                app_iter.close()
        except:
            if hasattr(app_iter, 'close'):
                app_iter.close()

            #we need that here
            exc_type, exc_value, tb = sys.exc_info()
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
            if self.catch_callback:
                try:
                    self.callback(traceback, environ)
                except Exception, e:
                    log.error(
                        'ERRORMATOR: Exception in logging callback: %s' % e)
            else:
                self.callback(traceback, environ)
            # by default reraise exceptions for app/FW to handle
            if self.errormator.reraise_exceptions:
                raise exc_type, exc_value, tb
            try:
                start_response('500 INTERNAL SERVER ERROR',
                        [('Content-Type', 'text/html; charset=utf-8')])
            except Exception:
                # if we end up here there has been output but an error
                # occurred.  in that situation we can do nothing fancy any
                # more, better log something into the error log and fall
                # back gracefully.
                environ['wsgi.errors'].write(
                    'TracebackCatcher middleware caught exception in streamed '
                    'response at a point where response headers were already '
                    'sent.\n')
            else:
                yield 'Server Error'


#above original Traceback Catcher for reference

class ErrormatorBase(object):

    __version__ = 0.2

    def __init__(self, app, config, log_handler=None):
        self.app = app
        self.enabled = asbool(config.get('errormator', True))
        self.server = config.get('errormator.server') or fqdn
        self.async = asbool(config.get('errormator.async', True))
        self.catch_callback = asbool(
                config.get('errormator.catch_callback', True))
        self.client = config.get('errormator.client', 'python')
        self.api_key = config.get('errormator.api_key')
        self.server_url = config.get('errormator.server_url')
        self.buffer_flush_time = int(config.get('errormator.buffer_flush_time', 60))
        self.timeout = int(config.get('errormator.timeout', 20))
        self.gzip = asbool(config.get('errormator.gzip', False))
        self.reraise_exceptions = asbool(
                config.get('errormator.reraise_exceptions', True))
        self.slow_request = asbool(config.get('errormator.slow_request', False))
        self.slow_request_time = float(config.get('errormator.slow_request.time', 10))
        self.slow_query_time = float(config.get('errormator.slow_query.time', 5))
        if self.slow_request_time < 1:
            self.slow_request_time = 1.0
        if self.slow_query_time < 1:
            self.slow_query_time = 1.0
        self.slow_request_time = datetime.timedelta(seconds=self.slow_request_time)
        self.slow_query_time = datetime.timedelta(seconds=self.slow_query_time)
        self.log_handler = log_handler

    def data_filter(self, structure, section=None): 
        if section == 'error_report':
            keys_to_check = (structure['report_details'][0]['request'].get('ERRORMATOR_COOKIES'),
                              structure['report_details'][0]['request'].get('ERRORMATOR_GET'),
                              structure['report_details'][0]['request'].get('ERRORMATOR_POST')
                              )        
        elif section == 'slow_request':
            keys_to_check = (structure['request'].get('ERRORMATOR_COOKIES'),
                              structure['request'].get('ERRORMATOR_GET'),
                              structure['request'].get('ERRORMATOR_POST')
                              )
        else:
            # do not filter for 404 by default
            return structure
        
        for source in filter(None,keys_to_check):
            for k, v in source.items():
                if ('password' in k or 'passwd' in k or 'pwd' in k 
                    or 'auth_tkt' in k):
                    source[k] = u'***'
        return structure


class ErrormatorCatcher(ErrormatorBase):

    __version__ = 0.2

    def generate_report(self, environ, traceback=None, message=None, http_status=200):
        parsed_data, additional_info = create_report_structure(environ,
                                                               traceback,
                                                               message,
                                                               http_status,
                                                               server=self.server
                                                               )
        if traceback:
            exception_text = traceback.exception
            traceback_text = traceback.plaintext
            parsed_data['error_type'] = exception_text
            parsed_data['traceback'] = traceback_text
        else:
            parsed_data['error_type'] = '404 Not Found'
        if parsed_data['http_status'] == 404 and \
                parsed_data.get('traceback'):
            #make sure traceback is empty for 404's
            parsed_data['traceback'] = u''
        #lets populate with additional environ data
        parsed_data.update(additional_info)
        parsed_data['errormator.client'] = self.client
        if traceback:
            parsed_data = self.data_filter(parsed_data, 'error_report')
        else:
            parsed_data = self.data_filter(parsed_data, '404_report')
        return parsed_data

    def __call__(self, environ, start_response):
        """Run the application and conserve the traceback frames.
        also determine if we got 404
        """
        app_iter = None
        detected_data = []
        try:
            #inject local reporting function to environ
            if 'errormator.report' not in environ:
                def local_report(message, include_traceback=True,
                                 http_status=200):
                    if include_traceback:
                        traceback = get_current_traceback(skip=1,
                                show_hidden_frames=True,
                                ignore_system_exceptions=True)
                    else:
                        traceback = None
                    report = self.generate_report(environ, traceback,
                                    message=message, http_status=500)
                    error_call = RemoteCall([report])
                    error_call.submit(self.api_key, self.server_url,
                            timeout=self.timeout,
                            endpoint='/api/reports')

                environ['errormator.report'] = local_report

            #inject remote logging function to environ
            if 'errormator.log' not in environ:
                def local_log(level, message):
                    log_call = RemoteCall([
                        {"log_level":level,
                        "message":message,
                        "timestamp":datetime.datetime.utcnow().isoformat(),
                        "server":self.server
                        }])
                    log_call.submit(self.api_key, self.server_url,
                            timeout=self.timeout,
                            endpoint='/api/logs')

                environ['errormator.log'] = local_log
            
            app_iter = self.app(environ, start_response)
            return app_iter
                
#            for item in app_iter:
#                yield item
#            if hasattr(app_iter, 'close'):
#                app_iter.close()
#
#            if detected_data and detected_data[0] == '404':
#                self.report(environ)
        except:
            if hasattr(app_iter, 'close'):
                app_iter.close()
            #we need that here
            exc_type, exc_value, tb = sys.exc_info()
            traceback = get_current_traceback(skip=1, show_hidden_frames=True,
                                              ignore_system_exceptions=True)
            report = self.generate_report(environ, traceback,
                                    message=None, http_status=500)
            #leave trace of exception in logs
            log_errors.warning('%s @ %s' % (report.get('error_type'),
                                report['report_details'][0].get('url')),
                               extra={'errormator_data':report}
                      )
            # by default reraise exceptions for app/FW to handle
            if self.reraise_exceptions:
                raise exc_type, exc_value, tb
            try:
                start_response('500 INTERNAL SERVER ERROR',
                        [('Content-Type', 'text/html; charset=utf-8')])
            except Exception:
                # if we end up here there has been output but an error
                # occurred.  in that situation we can do nothing fancy any
                # more, better log something into the error log and fall
                # back gracefully.
                environ['wsgi.errors'].write(
                    'TracebackCatcher middleware catched exception in streamed'
                    ' response at a point where response headers were already'
                    ' sent.\n')
            else:
                return 'Server Error'

class ErrormatorReport404(ErrormatorCatcher):
    __version__ = 0.2
        
    def __call__(self, environ, start_response):
        """Run the application, determine if we got 404
        """
        app_iter = None
        detected_data = []

        def detect_headers(status, headers, *k, **kw):
            detected_data[:] = status[:3], headers
            return start_response(status, headers, *k, **kw)

        app_iter = self.app(environ, detect_headers)                
        try:
            return app_iter
        finally:
            #lets process environ
            if detected_data and detected_data[0] == '404':
                report = self.generate_report(environ, traceback=None,
                                    message=None, http_status=404)
                #leave trace of exception in logs
                log_errors.warning('%s @ %s' % (report.get('error_type'),
                                    report['report_details'][0].get('url')),
                                   extra={'errormator_data':report}
                          )
        
class ErrormatorSlowRequest(ErrormatorBase):
    __version__ = 0.2
    
    def generate_report(self, environ, start_time, end_time, records=[]):
        (parsed_request, remote_addr, additional_info) = \
                process_environ(environ, True)
        report = {
        "start_time":start_time.isoformat(),
        "end_time":end_time.isoformat(),
        "template_start_time":environ.get('errormator.tmpl_start_time'),
        "report_details":[],
        "server": self.server,
        "url": paste_req.construct_url(environ),
        "request":{
            "user_agent": environ.get('HTTP_USER_AGENT'),
            "username": environ.get('REMOTE_USER', u''),
            "ERRORMATOR_COOKIES":parsed_request['ERRORMATOR_COOKIES'],
            "ERRORMATOR_POST":parsed_request['ERRORMATOR_POST'],
            "ERRORMATOR_GET":parsed_request['ERRORMATOR_GET']}
                       }
        for record in records:
            report['report_details'].append(record.errormator_data)
        report = self.data_filter(report, 'slow_request')
        return report
    
    def __call__(self, environ, start_response):
        """Run the application, determine if we got 404
        """
        app_iter = None
        detected_data = []
        start_time = datetime.datetime.utcnow()
        app_iter = self.app(environ, start_response)                
        try:
            return app_iter
        finally:
            end_time = datetime.datetime.utcnow()
            delta = end_time - start_time
            records = self.log_handler.get_records()
            self.log_handler.clear_records()
            if delta >= self.slow_request_time or len(records) > 0: 
                report = self.generate_report(environ, start_time, end_time,
                                               records)
                log_slow_reports.info('slow request/queries detected: %s' % 
                                report.get('url'),
                                extra={'errormator_data':report}
                          )

#deprecated bw compat
class ErrormatorHTTPCodeSniffer(object):
    def __init__(self, app, config):
        self.app = app

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)


def make_errormator_middleware(app, global_config, **kw):
    config = global_config.copy()
    config.update(kw)
    #this shuts down all errormator functionalities
    if not asbool(config.get('errormator', True)):
        return app
    
    filter_callable = config.get('errormator.filter_callable')
    if filter_callable:
        try:
            parts = filter_callable.split(':')
            _tmp = __import__(parts[0], globals(), locals(), [parts[1],], -1)
            filter_callable = getattr(_tmp, parts[1])
            print filter_callable
        except ImportError, e:
            filter_callable = None
            log.error('Could not import filter callable, using default, %s' % e) 
    
    
    # batch error sending logger -> api
    error_handler = ErrormatorReportHandler(
                    capacity=int(config.get('errormator.error.buffer', 5)),
                    async=asbool(config.get('errormator.error.async', True)),
                    api_key=config.get('errormator.api_key'),
                    server_url=config.get('errormator.server_url'),
                    server_name=config.get('errormator.server_name'),
                    timeout=config.get('errormator.error.timeout', 30),
        buffer_flush_time=int(config.get('errormator.buffer_flush_time', 60)),
        endpoint='/api/reports'
                        )
    error_handler.setLevel(logging.DEBUG)
    logging.root.addHandler(error_handler)
    
    # general logging handler -> api
    if asbool(config.get('errormator.logging', True)):
        level = LEVELS.get(config.get('errormator.logging.level',
                                      'NOTSET').lower(),
                           logging.NOTSET)
        log_handler = ErrormatorLogHandler(
                    capacity=int(config.get('errormator.logging.buffer', 50)),
                    async=asbool(config.get('errormator.logging.async', True)),
                    api_key=config.get('errormator.api_key'),
                    server_url=config.get('errormator.server_url'),
                    server_name=config.get('errormator.server_name'),
                    timeout=int(config.get('errormator.logging.timeout', 30)),
                    buffer_flush_time=int(config.get('errormator.buffer_flush_time', 60))
                            )
        log_handler.setLevel(level)
        logging.root.addHandler(log_handler)

    if asbool(config.get('errormator.slow_request', False)):
        # batch error sending logger -> api - same as error handler but we dont
        # want to share buffers
        query_handler = ErrormatorReportHandler(
                        capacity=int(config.get('errormator.error.buffer', 5)),
                        async=asbool(config.get('errormator.error.async', True)),
                        api_key=config.get('errormator.api_key'),
                        server_url=config.get('errormator.server_url'),
                        server_name=config.get('errormator.server_name'),
                        timeout=config.get('errormator.error.timeout', 30),
            buffer_flush_time=int(config.get('errormator.buffer_flush_time', 60)),
            endpoint='/api/slow_reports'
                            )
        query_handler.setLevel(logging.DEBUG)
        logging.root.addHandler(query_handler)
        #register thread tracking handler
        thread_tracking_handler = ThreadTrackingHandler()
        logging.root.addHandler(thread_tracking_handler)
        thread_tracking_handler.setLevel(logging.DEBUG)
        #pass the threaded handler to middleware 
        app = ErrormatorSlowRequest(app, config=config,
                                    log_handler=thread_tracking_handler)
        if filter_callable:
            app.data_filter = filter_callable
        #register sqlalchemy listeners
        if asbool(config.get('errormator.slow_request.sqlalchemy', False)):
            try:
                from sqlalchemy import event
                from sqlalchemy.engine.base import Engine
                slow_query_time = float(config.get('errormator.slow_query.time', 5))
                if slow_query_time < 1:
                    slow_query_time = 1.0
                tdelta = datetime.timedelta(seconds=slow_query_time)
                sqlalchemy_07_listener(tdelta)
            except ImportError, e:
                log.warning('Sqlalchemy older than 0.7 - logging disabled')


    if asbool(config.get('errormator.report_404', False)):
        app = ErrormatorReport404(app, config=config)
        if filter_callable:
            app.data_filter = filter_callable
    
    if asbool(config.get('errormator.report_errors', True)):
        app = ErrormatorCatcher(app, config=config)
        if filter_callable:
            app.data_filter = filter_callable
    return app

#alias for be compat
make_catcher_middleware = make_errormator_middleware 

def make_sniffer_middleware(app, global_config, **kw):
    #deprecated, errormator catcher will handle everything
    return app
