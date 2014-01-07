Running tests
=============

You can run the tests via the `test` command of setup.py.

::

     $ python setup.py test
     running test
     running egg_info
     writing requirements to appenlight_client.egg-info/requires.txt
     writing appenlight_client.egg-info/PKG-INFO
     ...

Tests for the timing instrumentation will not run if you do not have the relevant
packages installed. When you do have them installed the tests make a number of
assumptions about your system:

* the psycopg2 timing tests assume that they can connect to a PostgreSQL server
  running on 127.0.01 and connect with username *test*, password *test* to
  a database named *test*.

