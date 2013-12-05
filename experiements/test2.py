from appenlight_client import client
from appenlight_client.timing import time_trace
import time

class Foo(object):


    @time_trace(name='Foo.test', min_duration=0.1)
    def test(self):
        time.sleep(0.1)
        return 1

    @time_trace(name='Foo.__call__', min_duration=0.2)
    def __call__(self):
        time.sleep(0.5)
        return 2


inst = Foo()
print inst.test()
print inst()


timing_conf = client.get_config({'appenlight.api_key':'1234'})
for k, v in timing_conf.iteritems():
    if 'appenlight.timing' in k:
        timing_conf[k] = 0.00000001

client.Client(config=timing_conf)
from appenlight_client.timing import local_timing, get_local_storage



stats, slow_calls = get_local_storage(local_timing).get_thread_stats()
print 'calls', len(slow_calls), slow_calls
print 'stats', stats
