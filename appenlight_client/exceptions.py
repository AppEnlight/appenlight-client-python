import sys

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
import itertools
import traceback
import codecs
import collections
from appenlight_client.utils import PY3

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

def truncate_str(input):
    try:
        return unicode(input) if len(input) < 255 else unicode(input[:255]) + '...'
    except Exception:
        return '<failed-truncating>'

def serialize_to_unicode(input, treat_as_class=False):
    if isinstance(input, collections.Mapping):
        if hasattr(input, 'iterkeys'):
            dict_method = input.iterkeys
        else:
            dict_method = input.keys
    else:
        dict_method = None

    if dict_method is not None:
        # avoid sending environ
        if input.get('wsgi.version'):
            return dict([['environ', '<environ-skipped>']])
        dict_keys = itertools.takewhile(lambda x:x[0] < 128, enumerate(dict_method()))
        return dict([[repr(k), truncate_str(repr(input[k]))] for i, k in dict_keys])
    elif isinstance(input, (tuple, list, set, frozenset)):
        return [truncate_str(repr(v)) for i, v in
                itertools.takewhile(lambda x:x[0] < 128, enumerate(input))]
    elif isinstance(input, basestring):
        return truncate_str(input)
    else:
        to_return = repr(input)
        return truncate_str(to_return)

def shorten_filename(frame):
    filename = frame.filename
    if frame.module:
        try:
            # shorten filenames
            package = frame.module.split('.', 1)[0]
            base_filename = sys.modules[package].__file__
            to_trunc = base_filename.rsplit(os.sep, 2)[0]
            filename = filename.split(to_trunc, 1)[-1][1:]
        except Exception as e:
            pass
    return filename

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
    if not tb:
        return None
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
        if PY3:
            return ''.join(buf).strip()
        else:
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
                    (shorten_filename(frame), frame.lineno, frame.function_name,))
            result.append('    %s' % frame.current_line.strip())
        result.append('%s' % self.exception)
        return '\n'.join(result)

    id = property(lambda x: id(x))

    def frameinfo(self, include_vars=False, skip_existing=True):
        """Dict representing frame and variables"""
        result = []
        id_list = []
        for frame in self.frames:
            if frame.hide:
                continue
            entry = {'file':shorten_filename(frame), # file location
                     'line':frame.lineno, # line number
                     'fn':frame.function_name, # function name
                     'cline':frame.current_line.strip(), # current frame line
                     'vars':[]} # vars

            # in some situations frame.locals might be not something we expect
            if include_vars:
                if not isinstance(frame.locals, dict):
                    entry['vars'].append({'unknown': '<uninspectable>'})
                    continue
                for k, v in frame.locals.iteritems():
                    if id(v) not in id_list:
                        id_list.append(id(v))
                    else:
                        if skip_existing:
                            continue
                    try:
                        if k == 'self':
                            entry['vars'].append(['self.' + v.__class__.__name__,
                                                  serialize_to_unicode(v)])
                        else:
                            if k == 'environ':
                                entry['vars'].append([k, '<environ-skipped>'])
                                continue
                            entry['vars'].append([k, serialize_to_unicode(v)])
                    except Exception as e:
                        entry['vars'].append([k, '<unserializable>'])
            result.append(entry)
        result.append({'file':'',
                     'line':'',
                     'fn':'',
                     'cline':'%s' % self.exception,
                     'vars':[]}
                      )
        return result


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
# we actually dont want that or it will break filename shortening
#        if os.path.isfile(fn):
#            fn = os.path.realpath(fn)
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
                with open(self.filename) as f:
                    source = f.read()
            except (IOError, OSError) as e:
                return []
            except UnicodeDecodeError:
                #since there's no io/os exception we can assume that the file exists
                #so we will force it in utf-8
                with open(self.filename, encoding='utf-8') as f:
                    source = f.read()

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
