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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:
    import json
except (ImportError,), e:
    import simplejson as json

from paste import request as paste_req
from paste.util.converters import asbool
import sys
import urllib
import threading
import datetime
import socket
try:
    from email.mime.text import MIMEText
except:
    from email.MIMEText import MIMEText
import smtplib

import logging

#lets try to find fqdn
fqdn = socket.getfqdn()

class ErrormatorException(Exception):
    def _get_message(self): 
        return self._message
    def _set_message(self, message): 
        self._message = message
    message = property(_get_message, _set_message)
    def __str__(self):
        return repr(self.args)

class Report(object):
    
    def __init__(self, payload={}):
        self.payload = payload

    def submit(self, api_key, server_url,
               default_path='/api/reports',
               errormator_client='python',
               exception_on_failure=True):
        post_data = []
        for k, v in self.payload.items():
            if hasattr(v, 'encode'):
                post_data.append((k, v.encode('utf8'),))
            else:
                post_data.append((k, v,))
        post_data.append(('api_key', api_key,))
        post_data.append(('errormator.client', errormator_client,))
        post_data = urllib.urlencode(post_data)
        server_url = '%s%s' % (server_url, default_path,)
        try:
            conn = urllib.urlopen(server_url, post_data)
            if conn.getcode() != 200:
                message = 'ERRORMATOR: response code: %s' % conn.getcode()
                logging.error(message)
                if exception_on_failure:
                    raise ErrormatorException(message)
        except (IOError,), e:
            logging.error('ERRORMATOR: problem: %s' % e)
            if exception_on_failure:
                raise ErrormatorException(*e)
        message = '%s:ERRORMATOR: logged: %s' % (datetime.datetime.now(),
                                           self.payload['error_type'],)
        logging.error(message)

class AsyncReport(threading.Thread):
    
    def __init__ (self):
        super(AsyncReport, self).__init__()
        self.report = None
        self.config = {}
          
    def run (self):
        self.report.submit(
                self.config.get('errormator.api_key'),
                self.config.get('errormator.server_url'),
                errormator_client=self.config.get('errormator.client', 'python')
                           )

class ErrormatorCallback(object):
    
    def __init__(self, config_dict):
        self.config = config_dict.copy()
    
    @classmethod
    def process_environ(cls, environ):
        request_text = []
        additional_info = []
        for key, value in sorted(environ.items()):
            if key.startswith('errormator.'):
                additional_info.append((key[11:], unicode(value),))
            try:
                if hasattr(value, 'decode'):
                    request_text.append(u'%s: %s' % (key, value.decode('utf8'),))
                else:
                    request_text.append(u'%s: %s' % (key, value,))
            except:
                # this CAN go wrong
                pass
        
        if environ.get("HTTP_X_REAL_IP"):
            remote_addr = environ.get("HTTP_X_REAL_IP") 
        elif environ.get("HTTP_X_FORWARDED_FOR"):
            remote_addr = environ.get("HTTP_X_FORWARDED_FOR").split(',')[0].strip()
        else:
            remote_addr = environ.get('REMOTE_ADDR')
        return request_text, remote_addr, additional_info
         
    def __call__(self, traceback, environ):
        if not asbool(self.config.get('errormator', True)):
            return
        
        exception_text = traceback.exception
        traceback_text = traceback.plaintext          
        report = Report()
        (request_text,
         remote_addr,
         additional_info) = ErrormatorCallback.process_environ(environ)
        report.payload['http_status'] = 500
        report.payload['priority'] = 5
        report.payload['ip'] = remote_addr
        report.payload['user_agent'] = environ.get('HTTP_USER_AGENT')
        report.payload['url'] = paste_req.construct_url(environ)
        report.payload['error_type'] = exception_text
        report.payload['server'] = self.config.get('errormator.server')\
                    or fqdn or environ.get('SERVER_NAME', 'unknown server')
        report.payload['message'] = u''
        report.payload['traceback'] = traceback_text
        report.payload['request'] = u'\n'.join(request_text)
        report.payload['username'] = environ.get('REMOTE_USER')
        #lets populate with additional environ data
        report.payload.update(additional_info)
        if asbool(self.config.get('errormator.async', True)):
            report.submit(self.config.get('errormator.api_key'),
                self.config.get('errormator.server_url'),
                errormator_client=self.config.get('errormator.client', 'python')
                          )
        else:
            async_report = AsyncReport()
            async_report.report = report
            async_report.config = self.config
            async_report.start()
        
        
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
import sys
import inspect
import traceback
import codecs
from tokenize import TokenError


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

    def is_syntax_error(self):
        """Is it a syntax error?"""
        return isinstance(self.exc_value, SyntaxError)
    is_syntax_error = property(is_syntax_error)

    def exception(self):
        """String representation of the exception."""
        buf = traceback.format_exception_only(self.exc_type, self.exc_value)
        return ''.join(buf).strip().decode('utf-8', 'replace')
    exception = property(exception)

    def log(self, logfile=None):
        """Log the ASCII traceback into a file object."""
        if logfile is None:
            logfile = sys.stderr
        tb = self.plaintext.encode('utf-8', 'replace').rstrip() + '\n'
        logfile.write(tb)

    def plaintext(self):
        result = ['Traceback (most recent call last):']
        for frame in self.frames:
            result.append('File "%s", line %s, in %s' % (frame.filename, frame.lineno, frame.function_name,))
            result.append('    %s' % frame.current_line.strip()) 
        result.append('%s' % self.exception)
        return '\n'.join(result)
    plaintext = cached_property(plaintext)

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
                    logging.error('ERRORMATOR: Exception in logging callback: %s' % e)
            else:
                self.callback(traceback, environ)
            # by default reraise exceptions for app/FW to handle
            if asbool(self.config.get('errormator.reraise_exceptions', True)):
                raise exc_type, exc_value, tb                                   
            try:
                start_response('500 INTERNAL SERVER ERROR', [
                    ('Content-Type', 'text/html; charset=utf-8')
                ])
            except Exception, err:
                # if we end up here there has been output but an error
                # occurred.  in that situation we can do nothing fancy any
                # more, better log something into the error log and fall
                # back gracefully.
                environ['wsgi.errors'].write(
                    'TracebackCatcher middleware catched exception in streamed '
                    'response at a point where response headers were already '
                    'sent.\n')
            else:
                yield 'Server Error'


class ErrormatorCatcher(TracebackCatcher):
    def __init__(self, app, config):
        self.app = app
        self.callback = ErrormatorCallback(config)
        self.config = config
        if 'errormator.catch_callback' in config:
            self.catch_callback = asbool(config['errormator.catch_callback'])
        else:
            self.catch_callback = True

class ErrormatorHTTPCodeSniffer(object):
    def __init__(self, app, config):
        self.app = app
        self.config = config
        if 'errormator.catch_callback' in config:
            self.catch_callback = asbool(config['errormator.catch_callback'])
        else:
            self.catch_callback = True

    def callback(self, environ):
        report = Report()
        request_text, remote_addr = ErrormatorCallback.process_environ(environ)
        report.payload['http_status'] = 404
        report.payload['priority'] = 5
        report.payload['ip'] = remote_addr
        report.payload['user_agent'] = environ.get('HTTP_USER_AGENT')
        report.payload['url'] = paste_req.construct_url(environ)
        report.payload['error_type'] = '404 Not Found'
        report.payload['server'] = self.config.get('errormator.server')\
                    or fqdn or environ.get('SERVER_NAME', 'unknown server')
        report.payload['message'] = u''
        report.payload['traceback'] = ''
        report.payload['request'] = u'\n'.join(request_text)
        report.payload['username'] = environ.get('REMOTE_USER')
        if asbool(self.config.get('errormator.async', True)):
            report.submit(self.config.get('errormator.api_key'),
                self.config.get('errormator.server_url'),
                errormator_client=self.config.get('errormator.client', 'python')
                          )
        else:
            async_report = AsyncReport()
            async_report.report = report
            async_report.config = self.config
            async_report.start()
    
    def __call__(self, environ, start_response):
        detected_data = []
        def detect_headers(status, headers, *k, **kw):
            detected_data[:] = status[:3], headers
            return start_response(status, headers, *k, **kw)
        app_iter = self.app(environ, detect_headers)
        for item in app_iter:
            yield item
        if hasattr(app_iter, 'close'):
            app_iter.close()
        if detected_data and detected_data[0] == '404' \
                                and asbool(self.config.get('errormator', True)):
            if self.catch_callback:
                try:
                    self.callback(environ)
                except Exception, e:
                    logging.error('ERRORMATOR: Exception in logging callback: %s' % e)
                    pass
            else:
                self.callback(environ)
            


def make_catcher_middleware(app, global_config, **kw):
    config = global_config.copy()
    config.update(kw)
    return ErrormatorCatcher(app, config=config)

def make_sniffer_middleware(app, global_config, **kw):
    config = global_config.copy()
    config.update(kw)
    return ErrormatorHTTPCodeSniffer(app, config=config)
