from sqlalchemy import event
from sqlalchemy.engine.base import Engine
import datetime
import logging
# used for slow query GATHERING/ - to be picked up by threaded logger


def sqlalchemy_07_listener(delta, datastore_handler):
    log_slow = logging.getLogger('errormator_client.datastore.sqlalchemy')
    log_slow.setLevel(logging.DEBUG)
    log_slow.addHandler(datastore_handler)

    @event.listens_for(Engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, stmt, params, context, execmany):
        setattr(conn, 'err_query_start', datetime.datetime.utcnow())

    @event.listens_for(Engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, stmt, params, context, execmany):
        if not hasattr(conn,'err_query_start'):
            return
        td = datetime.datetime.utcnow() - conn.err_query_start
        if td >= delta:
            duration = float('%s.%s' % (
                        (td.seconds + td.days * 24 * 3600) * 10 ** 6 / 10 ** 6,
                             td.microseconds)
                             )
            query_info = {'type':'sqlalchemy',
                          'timestamp':conn.err_query_start,
                          'duration': duration,
                          'statement': stmt,
                          'parameters': params
                    }
            log_slow.debug('slow query detected',
                             extra={'errormator_data':query_info}
                              )
        delattr(conn, 'err_query_start')
