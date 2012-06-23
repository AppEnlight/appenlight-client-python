from decorator import decorator
import logging
import inspect
import datetime
import sys
import time
import threading

local_timing = threading.local()

from timeit import Timer

log = logging.getLogger(__name__)

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time


def caller_name(skip=2):
    """Get a name of a caller in the format module.class.method
`skip` specifies how many levels of stack to skip while getting caller
name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.
An empty string is returned if skipped levels exceed stack height
"""
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
      return ''
    parentframe = stack[start][0]
    
    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        # be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>': # top level usually
        name.append(codename) # function or a method
    del parentframe
    return ".".join(name)


def trace_factory(info_gatherer, min_duration):
    def _e_trace(f, *args, **kw):
        start = default_timer()
        result = f(*args, **kw)
        end = default_timer()
        duration = round(end - start, 4)
        if duration < min_duration:
            return result
        info = {'timestamp':start, 'duration':duration}
        info.update(info_gatherer(*args, **kw))
        stack = inspect.stack()
        for frame in stack:
            if frame[3] == '_e_trace':
                continue
            name = []
            module = inspect.getmodule(frame[0])
            if module:
                name.append(module.__name__)
            elif 'self' in frame[0].f_locals:
                name.append(frame[0].f_locals['self'].__class__.__name__)
                name.append(frame[3])
            else:
                name.append(frame[3])
            detail = (frame[0].f_lineno, '.'.join(name))
        if not hasattr(local_timing, '_errormator'):
            local_timing._errormator = {'slow_calls':{}}
        if detail not in local_timing._errormator['slow_calls']:
            local_timing._errormator['slow_calls'][detail] = info
        return result
    return _e_trace

def time_trace(f, gatherer, min_duration):
    return decorator(trace_factory(gatherer, min_duration), f)
