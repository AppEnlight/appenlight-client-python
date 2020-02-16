from __future__ import absolute_import
from appenlight_client.timing import get_local_storage
from appenlight_client.utils import fullyQualifiedName
from pyramid.tweens import EXCVIEW
import pkg_resources
import pyramid.config
import logging
import inspect

from functools import wraps

log = logging.getLogger(__name__)


# stolen from pyramid 1.4
def combine(*decorators):
    def decorated(view_callable):
        # reversed() is allows a more natural ordering in the api
        for decorator in reversed(decorators):
            view_callable = decorator(view_callable)
        return view_callable

    return decorated


def is_bound_method(ob):
    return inspect.ismethod(ob) and getattr(ob, '__self__', None) is not None


def _parse_version(version_str):
    # not sure how consistently these are installed, just try all of them
    try:
        from packaging import version
        return version.parse(version_str)
    except ImportError:
        pass

    try:
        from distutils.version import LooseVersion, StrictVersion
        try:
            return StrictVersion(version_str)
        except distutils.version.InvalidVersion:
            return LooseVersion(version_str)
    except ImportError:
        pass

    try:
        from setuptools import parse_version
        return parse_version(version_str)
    except ImportError:
        pass

    try:
        from pkg_resources import parse_version
        return parse_version(version_str)
    except ImportError:
        pass

    raise NotImplementedError(version_str)


# feature sniffing
def can_pyramid_version_append_decorator(pyramid_version_str):
    last_bad_ver = _parse_version('1.4a3')
    return _parse_version(pyramid_version_str) > last_bad_ver


can_append_decorator = can_pyramid_version_append_decorator(
    pkg_resources.get_distribution('pyramid').version,
)


def wrap_pyramid_view_method_name(appenlight_callable):
    """This add missing methods to name"""

    @wraps(appenlight_callable)
    def view_callable_wrapper(*args, **kwargs):
        appenlight_storage = get_local_storage()
        if hasattr(appenlight_storage, 'view_name'):
            try:
                split_name = appenlight_storage.view_name.split(':')
                # only change the name if it wasn't resolved yet
                if len(split_name) == 2 and '.' not in split_name[1]:
                    appenlight_storage.view_name = '%s.%s' % (appenlight_storage.view_name,
                                                              appenlight_callable.__name__)
            except Exception:
                pass
        return appenlight_callable(*args, **kwargs)

    return view_callable_wrapper


def wrap_pyramid_view_name(appenlight_callable):
    @wraps(appenlight_callable)
    def view_callable_wrapper(context, request):
        appenlight_storage = get_local_storage()
        view_name = ''
        try:
            original_view = getattr(appenlight_callable, '__original_view__')
            if original_view:
                view_name = fullyQualifiedName(appenlight_callable)
                # fix the problem with bound methods,
                # we have to attach the resolved view name somehow.
                if is_bound_method(original_view):
                    _original_view = original_view
                    def original_view(context, request):
                        return _original_view(context, request)

                if not hasattr(original_view, '_appenlight_name'):
                    original_view._appenlight_name = view_name
        except Exception:
            raise
        if 'pyramid/static' in view_name:
            # normalize static views
            view_name = 'pyramid/static'
        if not getattr(appenlight_storage, 'view_name', None):
            appenlight_storage.view_name = view_name
        return appenlight_callable(context, request)

    # do not decorate view more than once, also decorate original class methods
    try:
        original_view = getattr(appenlight_callable, '__original_view__', None)
        if not hasattr(original_view, '_appenlight_wrapped_view'):
            original_view._appenlight_wrapped_view = True
            if original_view and inspect.isclass(original_view):
                for k, v in original_view.__dict__.items():
                    if not k.startswith('_') and inspect.isfunction(v):
                        setattr(original_view, k, wrap_pyramid_view_method_name(v))
    except Exception:
        pass
    return view_callable_wrapper


def wrap_view_config(appenlight_callable):
    @wraps(appenlight_callable)
    def wrapper(*args, **kwargs):
        view_config_decorator = kwargs.get('decorator', None)
        if view_config_decorator is not None:
            if isinstance(view_config_decorator, (list, tuple)):
                view_config_decorator = list(view_config_decorator)
            else:
                view_config_decorator = [view_config_decorator]

        if hasattr((kwargs.get('view')), '__view_defaults__'):
            view_defaults_decorator = kwargs.get('view').__view_defaults__.get('decorator', None)
            if view_defaults_decorator is not None:
                if isinstance(view_defaults_decorator, (list, tuple)):
                    view_defaults_decorator = list(view_defaults_decorator)
                else:
                    view_defaults_decorator = [view_defaults_decorator]
        else:
            view_defaults_decorator = None

        if can_append_decorator:
            if view_defaults_decorator is not None:
                if view_config_decorator is not None:
                    kwargs['decorator'] = view_defaults_decorator + view_config_decorator + [wrap_pyramid_view_name]
                else:
                    kwargs['decorator'] = view_defaults_decorator + [wrap_pyramid_view_name]
            else:
                if view_config_decorator is not None:
                    kwargs['decorator'] = view_config_decorator + [wrap_pyramid_view_name]
                else:
                    kwargs['decorator'] = [wrap_pyramid_view_name]

        return appenlight_callable(*args, **kwargs)

    return wrapper


def appenlight_tween_factory(handler, registry):
    blacklist = (pyramid.httpexceptions.WSGIHTTPException,)

    def error_tween(request):
        try:
            response = handler(request)
        except blacklist:
            raise
        except:
            if 'appenlight.client' in request.environ:
                # pass the traceback object to middleware
                request.environ[
                    'appenlight.__traceback'] = request.environ['appenlight.client'].get_current_traceback()
            raise
        # finally:
        #     appenlight_storage = get_local_storage()
        #     print appenlight_storage.view_name
        return response

    return error_tween


def includeme(config):
    config.add_tween(
        'appenlight_client.ext.pyramid_tween.appenlight_tween_factory',
        under=EXCVIEW)
    setattr(pyramid.config.Configurator, 'add_view',
            wrap_view_config(pyramid.config.Configurator.add_view))
