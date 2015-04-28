from __future__ import absolute_import
import logging
from celery.signals import task_failure, task_postrun, task_prerun, after_setup_logger
from appenlight_client.ext.general import gather_data
from datetime import datetime

log = logging.getLogger(__name__)
logging.basicConfig()


def register_signals(APPENLIGHT_CLIENT):

    def prerun_signal(sender, task_id, task, args, kwargs, *aargs, **kwds):
        task._appenlight_start_time = datetime.utcnow()

    def postrun_signal(sender, task_id, task, args, kwargs, retval, *aargs, **kwds):
        end_time = datetime.utcnow()
        start_time = getattr(task, '_appenlight_start_time')
        fake_environ = {'appenlight.view_name': 'celery:' + sender.name}
        gather_data(APPENLIGHT_CLIENT, fake_environ, gather_exception=False,
                    start_time=start_time, end_time=end_time)

    def failure_signal(sender, task_id, exception, args, kwargs, traceback,
                       einfo, *aargs, **kwds):
        end_time = datetime.utcnow()
        start_time = getattr(sender, '_appenlight_start_time')
        fake_environ = {'appenlight.view_name': 'celery:' + sender.name}
        gather_data(APPENLIGHT_CLIENT, fake_environ,
                    start_time=start_time, end_time=end_time)

    def after_setup_logger_signal(sender=None, logger=None, loglevel=None,
                                  logfile=None, format=None,
                                  colorize=None, **kwargs):
        if APPENLIGHT_CLIENT.config['logging'] and APPENLIGHT_CLIENT.config['enabled']:
            APPENLIGHT_CLIENT.register_logger(logger)

    task_prerun.connect(prerun_signal, weak=False)
    task_postrun.connect(postrun_signal, weak=False)
    task_failure.connect(failure_signal, weak=False)
    task_failure.connect(failure_signal, weak=False)
    after_setup_logger.connect(after_setup_logger_signal, weak=False)
    return True