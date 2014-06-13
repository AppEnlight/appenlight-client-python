from appenlight_client.utils import import_module, deco_func_or_method
from appenlight_client.timing import time_trace


ignore_set = frozenset()

to_decorate = ['bgrewriteaof', 'bgsave', 'config_get', 'config_set',
               'dbsize', 'debug_object', 'delete', 'echo', 'flushall',
               'flushdb',
               'hdel', 'hexists', 'hget', 'hgetall', 'hincrby', 'hkeys',
               'hlen', 'hset', 'hsetnx', 'hmset', 'hmget', 'hvals',
               'info', 'lastsave', 'object', 'ping', 'save',
               'shutdown', 'slaveof', 'append', 'decr', 'exists',
               'expire', 'expireat', 'get', 'getbit', 'getset', 'incr',
               'keys', 'mget', 'mset', 'msetnx', 'move', 'persist', 'publish',
               'randomkey', 'rename', 'renamenx', 'set', 'setbit',
               'setex', 'setnx', 'setrange', 'strlen', 'substr', 'ttl',
               'type', 'blpop', 'brpop', 'brpoplpush', 'lindex',
               'linsert', 'llen', 'lpop', 'lpush', 'lpushx', 'lrange',
               'lrem', 'lset', 'ltrim', 'rpop', 'rpoplpush', 'rpush',
               'rpushx', 'sort', 'sadd', 'scard', 'sdiff', 'sdiffstore',
               'sinter', 'sinterstore', 'sismember', 'smembers',
               'smove', 'spop', 'srandmember', 'srem', 'sunion',
               'sunionstore', 'zadd', 'zcard', 'zcount', 'zincrby',
               'zinterstore', 'zrange', 'zrangebyscore', 'zrank', 'zrem',
               'zremrangebyrank', 'zremrangebyscore', 'zrevrange',
               'zrevrangebyscore', 'zrevrank', 'zscore', 'zunionstore']


def add_timing(min_duration=0.1):
    module = import_module('redis')
    if not module:
        return

    def general_factory(slow_call_name):
        def gather_args(self, *args, **kwargs):
            return {'type': 'nosql', 'subtype': 'redispy',
                    'count': True,
                    'statement': slow_call_name,
                    'ignore_in': ignore_set}

        return gather_args

    if hasattr(module, 'StrictRedis'):
        for m in to_decorate:
            deco_func_or_method(module, 'StrictRedis.%s' % m, time_trace,
                                gatherer=general_factory('%s' % m), min_duration=min_duration)
    else:
        for m in to_decorate:
            deco_func_or_method(module, 'Redis.%s' % m, time_trace,
                                gatherer=general_factory('%s' % m), min_duration=min_duration)
