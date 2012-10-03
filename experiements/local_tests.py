import logging
import datetime
from errormator_client.timing import ErrormatorLocalStorage, register_timing, local_timing
logging.basicConfig()
logging.root.setLevel('DEBUG')

register_timing({'timing':{'dbapi2_psycopg2':0.0001,
                           'dbapi2_pg8000':0.0001,
                           'mongo':0.0001,
                           }})

import pymongo
from pymongo import Connection

connection = Connection()

'2.0.1'

db = connection.test_database
#print db
collection = db.test_collection
#print collection

posts = db.posts
db.collection_names()
for x in posts.find({"author": "MikeA"}):
    pass
posts.find_one({"author": "MikeB"})
posts.count()
for row in posts.find({"author": "Mike"}).sort("author"):
    row

for v in local_timing._errormator.get_slow_calls():
    print v
