import logging

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


def deco_func_or_method(module, name, deco_f, gatherer, min_duration,
                        is_template=False):
    _tmp = name.split('.')
    e_callable = getattr(module, _tmp[0], None)
    # decorate and set new value for foo.bar
    if len(_tmp) == 1 and e_callable:
        # _e_attached_tracer means this is already decorated
        # so don't do it twice - should not often happen in production,
        # but very important for tests
        if hasattr(e_callable, '_e_attached_tracer'):
            return
        e_callable = deco_f(e_callable, gatherer, min_duration, is_template)
        setattr(module, _tmp[0], e_callable)
    # decorate and set new value for foo.Bar.baz
    elif len(_tmp) > 1 and e_callable:
        cls_to_update = e_callable
        e_callable = getattr(e_callable, _tmp[1], None)
        if e_callable:
            if hasattr(e_callable, '_e_attached_tracer'):
                return
            setattr(cls_to_update, _tmp[1],
                    deco_f(getattr(e_callable, 'im_func', e_callable), gatherer,
                           min_duration, is_template))
    else:
        log.debug("can't decorate %s " % name)
