import logging
import datetime
from errormator_client.timing import ErrormatorLocalStorage, register_timing, local_timing
logging.basicConfig()
logging.root.setLevel('DEBUG')

''' http libs '''

import urllib
import urllib2
import urllib3
import threading
import requests
import httplib

''' dbapi2 libs '''

import pg8000
import psycopg2
import MySQLdb
import sqlite3
import oursql
import pyodbc
import pymysql

register_timing({'timing':{'dbapi2_psycopg2':0.0001,
                           'dbapi2_pg8000':0.0001,
                           }})


''' HTTP lib tests'''

#print '\n\n URLopener.open \n\n'
#opener = urllib.URLopener()
#f = opener.open("http://www.points2shop.com")
#
#print '\n\n urlretrieve \n\n' 
#urllib.urlretrieve('http://www.points2shop.com')
#
#print '\n\n urllib2 \n\n'
#urllib2.urlopen('http://www.points2shop.com')
#
#print '\n\n urllib3 \n\n'
#http = urllib3.PoolManager()
#r = http.request('GET', 'http://www.points2shop.com')
#
#print '\n\n requests \n\n'
#r = requests.get('http://www.points2shop.com')
#
#print '\n\n httplib \n\n'
#h2 = httplib.HTTPSConnection('www.points2shop.com')
#h2.request("GET", "/")


''' dbapi2 tests '''

print 'psycopg2'
conn = psycopg2.connect("dbname=test user=postgres host=127.0.0.1")
cur = conn.cursor()
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cur)
cur.execute("CREATE TEMPORARY TABLE test (id serial PRIMARY KEY, num integer, data varchar);")
cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))
cur.execute("SELECT * FROM test;")
cur.fetchone()
conn.commit()
cur.close()
conn.close()
print 'pg8000'
conn = pg8000.DBAPI.connect(host="localhost", user="test", password="test")
cursor = conn.cursor()
cursor.execute("CREATE TEMPORARY TABLE book (id SERIAL, title TEXT)")
cursor.execute(
     "INSERT INTO book (title) VALUES (%s), (%s) RETURNING id, title",
     ("Ender's Game", "Speaker for the Dead"))
for row in cursor:
    id, title = row
conn.commit()
cursor.execute("SELECT now()")
cursor.fetchone()
cursor.execute("SELECT now() - %s", (datetime.date(1980, 4, 27),))
cursor.fetchone()
pg8000.DBAPI.paramstyle = "numeric"
cursor.execute("SELECT array_prepend(:1, :2)", (500, [1, 2, 3, 4],))
cursor.fetchone()
cursor.close()
conn.close()
print 'postgresql'
#db = postgresql.open('pq://user:password@host:port/database')
#db.execute("CREATE TABLE emp (emp_first_name text, emp_last_name text, emp_salary numeric)")
#make_emp = db.prepare("INSERT INTO emp VALUES ($1, $2, $3)")
#make_emp("John", "Doe", "75,322")

print 'mysqldb'

db = MySQLdb.connect(passwd="test", user="test")
c = db.cursor()
c.execute("""SELECT 5/2 """)
c.fetchone()

print 'oursql'


conn = oursql.connect(host='127.0.0.1', user='test', passwd='test', port=3306,db='dejong_pointstoshop')
curs = conn.cursor(oursql.DictCursor)
curs.execute('SELECT * from users limit 10')
print curs.rowcount 

print 'sqlite3'
conn = sqlite3.connect(':memory:')
c = conn.cursor()
c.execute('''CREATE TABLE stocks
             (date text, trans text, symbol text, qty real, price real)''')
c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
conn.commit()
c.close()
print 'odbc'
cnxn = pyodbc.connect('Driver={MySQL};Server=127.0.0.1;Port=3306;Database=information_schema;User=test; Password=test;Option=3;')
cursor = cnxn.cursor()

#select all tables from all databases
cursor.execute("select 1+5,'odbc '")
rows = cursor.fetchall()
print 'pymsql'
conn = pymysql.connect(host='127.0.0.1', user='test', passwd='test')
c = conn.cursor()
c.execute('SELECT 5+%s,"%s"', (2,'pymysql'))
print c.fetchone()


print '\n\n\n'
for v in local_timing._errormator.get_slow_calls():
    print v
