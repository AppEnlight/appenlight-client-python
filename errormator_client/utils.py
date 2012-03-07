from webob import Request
import datetime
import json


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


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def process_environ(environ, traceback=None, include_params=False):
    # form friendly to json encode
    parsed_environ = {}
    errormator_info = {}
    req = Request(environ)
    for key, value in req.environ.items():
        if key.startswith('errormator.') and key not in ('errormator.client',
                                                    'errormator.force_send',
                                                    'errormator.log',
                                                    'errormator.report'):
            errormator_info[key[11:]] = unicode(value)
        else:
            if traceback or key.startswith('HTTP') or key in ('HTTP_USER_AGENT',):
                try:
                    if isinstance(value, str):
                        parsed_environ[key] = value.decode('utf8')
                    else:
                        parsed_environ[key] = unicode(value)
                except Exception as e:
                    pass
    # provide better details for 500's
    if include_params:
        parsed_environ['COOKIES'] = dict(req.cookies)
        parsed_environ['GET'] = dict([(k, req.GET.getall(k)) for k in req.GET])
        parsed_environ['POST'] = dict([(k, req.POST.getall(k))
                                       for k in req.POST])
    # figure out real ip
    if environ.get("HTTP_X_FORWARDED_FOR"):
        remote_addr = environ.get("HTTP_X_FORWARDED_FOR").split(',')[0].strip()
    else:
        remote_addr = (environ.get("HTTP_X_REAL_IP")
                       or environ.get('REMOTE_ADDR'))
    parsed_environ['REMOTE_ADDR'] = remote_addr
    errormator_info['URL'] = req.url
    return parsed_environ, errormator_info


def create_report_structure(environ, traceback=None, message=None,
            http_status=200, server='unknown server', include_params=False):
    (parsed_environ, errormator_info) = process_environ(environ, traceback,
                                                        include_params)
    report_data = {'client': 'Python', 'report_details': []}
    if traceback:
        exception_text = traceback.exception
        traceback_text = traceback.plaintext
        report_data['error_type'] = exception_text
        report_data['traceback'] = traceback_text
    report_data['http_status'] = 500 if traceback else http_status
    if http_status == 404:
        report_data['error_type'] = '404 Not Found'
    report_data['priority'] = 5
    report_data['server'] = (server or
                environ.get('SERVER_NAME', 'unknown server'))
    detail_entry = {}
    detail_entry['request'] = parsed_environ
    # fill in all other required info
    detail_entry['ip'] = parsed_environ.get('REMOTE_ADDR', u'')
    detail_entry['user_agent'] = parsed_environ.get('HTTP_USER_AGENT', u'')
    detail_entry['username'] = parsed_environ.get('REMOTE_USER', u'')
    detail_entry['url'] = errormator_info.pop('URL', 'unknown')
    if 'request_id' in errormator_info:
        detail_entry['request_id'] = errormator_info.pop('request_id', None)
    detail_entry['message'] = message or errormator_info.get('message', u'')
    #conserve bandwidth pop keys that we dont need in request details
    exclude_keys = ('HTTP_USER_AGENT', 'REMOTE_ADDR', 'HTTP_COOKIE',
                    'webob._parsed_cookies', 'webob._parsed_post_vars',
                    'webob._parsed_query_vars', 'errormator.client')
    for k in exclude_keys:
        detail_entry['request'].pop(k, None)
    report_data['report_details'].append(detail_entry)
    report_data.update(errormator_info)
    return report_data, errormator_info
