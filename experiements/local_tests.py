import logging
import datetime
from errormator_client.timing import ErrormatorLocalStorage, register_timing, local_timing
logging.basicConfig()
logging.root.setLevel('DEBUG')

register_timing({'timing':{'dbapi2_psycopg2':0.0001,
                           'dbapi2_pg8000':0.0001,
                           }})

for v in local_timing._errormator.get_slow_calls():
    print v
