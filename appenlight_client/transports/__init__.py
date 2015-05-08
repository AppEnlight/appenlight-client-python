import threading
import datetime
import logging

log = logging.getLogger(__name__)

class BaseTransport(object):

    def __init__(self, client_config):
        self.report_queue = []
        self.report_queue_lock = threading.RLock()
        self.log_queue = []
        self.log_queue_lock = threading.RLock()
        self.request_stats = {}
        self.request_stats_lock = threading.RLock()
        self.last_submit = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=50)
        self.last_request_stats_submit = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=50)
        self.client_config = client_config

    def purge(self):
        self.report_queue = []
        self.log_queue = []
        self.request_stats = {}

    def save_request_stats(self, stats, view_name):
        with self.request_stats_lock:
            req_time = datetime.datetime.utcnow().replace(second=0,
                                                          microsecond=0)
            if req_time not in self.request_stats:
                self.request_stats[req_time] = {}
            if view_name not in self.request_stats[req_time]:
                self.request_stats[req_time][view_name] = {'main': 0,
                                                                     'sql': 0,
                                                                     'nosql': 0,
                                                                     'remote': 0,
                                                                     'tmpl': 0,
                                                                     'unknown': 0,
                                                                     'requests': 0,
                                                                     'custom': 0,
                                                                     'sql_calls': 0,
                                                                     'nosql_calls': 0,
                                                                     'remote_calls': 0,
                                                                     'tmpl_calls': 0,
                                                                     'custom_calls': 0}
            self.request_stats[req_time][view_name]['requests'] += 1
            for k, v in stats.iteritems():
                self.request_stats[req_time][view_name][k] += v

    def check_if_deliver(self, force_send=False):
        delta = datetime.datetime.utcnow() - self.last_submit
        metrics = []
        reports = []
        logs = []
        # should we send
        if delta > self.client_config['buffer_flush_interval'] or force_send:
            # build data to feed the transport
            with self.report_queue_lock:
                reports = self.report_queue[:250]
                if self.client_config['buffer_clear_on_send']:
                    self.report_queue = []
                else:
                    self.report_queue = self.report_queue[250:]

            with self.log_queue_lock:
                logs = self.log_queue[:2000]
                if self.client_config['buffer_clear_on_send']:
                    self.log_queue = []
                else:
                    self.log_queue = self.log_queue[2000:]
            # mark times
            self.last_submit = datetime.datetime.utcnow()

        # metrics we should send every 60s
        delta = datetime.datetime.utcnow() - self.last_request_stats_submit
        if delta >= datetime.timedelta(seconds=60):
            with self.request_stats_lock:
                request_stats = self.request_stats
                self.request_stats = {}
            for k, v in request_stats.iteritems():
                metrics.append({
                    "server": self.client_config['server_name'],
                    "metrics": v.items(),
                    "timestamp": k.isoformat()
                })
            # mark times
            self.last_request_stats_submit = datetime.datetime.utcnow()

        if reports or logs or metrics:
            try:
                self.submit(reports=reports, logs=logs, metrics=metrics)
            except Exception as exc:
                log.error('APPENLIGHT: problem with transport submit: %s' % exc)
            return True
        return False