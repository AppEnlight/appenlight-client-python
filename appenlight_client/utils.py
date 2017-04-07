import datetime
import inspect
import logging
import os
import sys
import pkg_resources

# are we running python 3.x ?
PY3 = sys.version_info[0] >= 3

log = logging.getLogger(__name__)


def asbool(obj):
    if isinstance(obj, (str, unicode)):
        obj = obj.strip().lower()
        if obj in ['true', 'y', 't', '1']:
            return True
        elif obj in ['false', 'n', 'f', '0']:
            return False
        else:
            raise ValueError(
                "String is not true/false: %r" % obj)
    return bool(obj)


def aslist(obj, sep=None, strip=True):
    if isinstance(obj, basestring):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return obj
    elif obj is None:
        return []
    else:
        return [obj]


def import_module(name):
    try:
        return __import__(name, globals(), locals(), [], 0)
    except ImportError as e:
        log.debug('Could not import module: %s' % e)


def import_from_module(name):
    try:
        parts = name.split(':')
        _tmp = __import__(parts[0], globals(), locals(), [parts[1], ], 0)
        return getattr(_tmp, parts[1])
    except ImportError as e:
        log.debug('Could not import from module: %s' % e)


def deco_func_or_method(module, name, deco_f, single_attach_marker='_e_attached_tracer', **kwargs):
    """
    accepts a module and decorator factory function, then passes kwargs to the
    decorator factory and decorates the `name` object/method from module
    """
    _tmp = name.split('.')
    e_callable = getattr(module, _tmp[0], None)
    # decorate and set new value for foo.bar
    if len(_tmp) == 1 and e_callable:
        # _e_attached_tracer means this is already decorated
        # so don't do it twice - should not often happen in production,
        # but very important for tests
        if hasattr(e_callable, single_attach_marker):
            return
        e_callable = deco_f(**kwargs)(e_callable)
        setattr(module, _tmp[0], e_callable)
    # decorate and set new value for foo.Bar.baz
    elif len(_tmp) > 1 and e_callable:
        cls_to_update = e_callable
        e_callable = getattr(e_callable, _tmp[1], None)
        if e_callable:
            if hasattr(e_callable, single_attach_marker):
                return
            setattr(cls_to_update, _tmp[1], deco_f(**kwargs)(getattr(e_callable, 'im_func', e_callable)))
    else:
        log.debug("can't decorate %s " % name)


def resolveModule(module_name):
    module = sys.modules.get(module_name, None)
    if module:
        to_trunc = module.__file__.rsplit(os.sep, 2)[0]
        filename = module.__file__.split(to_trunc, 1)[-1][1:]
        filename = os.path.splitext(filename)[0]
    return filename


# from http://twistedmatrix.com/trac/browser/trunk/twisted/python/deprecate.py
# License MIT: http://twistedmatrix.com/trac/browser/trunk/LICENSE


def fullyQualifiedName(obj):
    if hasattr(obj, '_appenlight_name'):
        return obj._appenlight_name
    name = '<unknown>'
    try:
        name = obj.__qualname__
    except AttributeError:
        name = obj.__name__

    if inspect.isclass(obj) or inspect.isfunction(obj):
        moduleName = obj.__module__
        try:
            moduleName = resolveModule(moduleName)
        except Exception:
            pass
        name = "%s:%s" % (moduleName, name)
    elif inspect.ismethod(obj):
        try:
            cls = obj.__self__.__class__ if PY3 else obj.im_class
        except AttributeError:
            # Python 3 eliminates im_class, substitutes __module__ and
            # __qualname__ to provide similar information.
            name = "%s:%s" % (obj.__module__, obj.__qualname__)
        else:
            className = fullyQualifiedName(cls)
            name = "%s.%s" % (className, name)
    try:
        if hasattr(obj, '__func__'):
            obj.__func__._appenlight_name = name
        else:
            obj._appenlight_name = name
    except Exception:
        pass
    return name


def parse_tag(k, v):
    if isinstance(v, (basestring, datetime.datetime, datetime.date, float, int)):
        return (k, v,)
    else:
        return (k, unicode(v),)


class Version(object):
    def __init__(self, version_str):
        data = version_str.strip().split('.')
        self.major = int(data[0])
        self.minor = int(data[1])
        self.patch = int(data[2])

    def __str__(self):
        return '{}.{}.{}'.format(self.major, self.minor, self.patch)

def filter_callable(config, structure, section=None):
    def filter_dict(f_input, dict_method):
        for k in dict_method():
            for bad_key in config['request_keys_blacklist']:
                if bad_key in k.lower():
                    f_input[k] = u'***'

    keys_to_check = ()
    if section in ['error_report', 'slow_report']:
        keys_to_check = (
            structure['request'].get('COOKIES'),
            structure['request'].get('POST'),
        )
    for source in filter(None, keys_to_check):
        if hasattr(source, 'iterkeys'):
            filter_dict(source, source.iterkeys)
        elif hasattr(source, 'keys'):
            filter_dict(source, source.keys)
            # try to filter local frame vars, to prevent people
            #  leaking as much data as possible when enabling frameinfo
    frameinfo = structure.get('traceback')
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
                    for bad_key in config['request_keys_blacklist']:
                        if bad_key in source[0].lower():
                            source[1] = u'***'
    return structure
