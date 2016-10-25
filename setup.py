import appenlight_client
from setuptools import setup, find_packages

setup(name='appenlight_client',
      version=appenlight_client.__version__,
      description='Client for AppEnlight reporting - WSGI applications and django monitoring (http://getappenlight.com)',
      long_description=open("README.rst").read(),
      keywords = "monitoring, wsgi, django, flask, pylons, pyramid, debugging, debug, reporting, errors, errormator, appenlight client, sentry alternative",
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Web Environment',
          'Framework :: BFG',
          'Framework :: CherryPy',
          'Framework :: Django',
          'Framework :: Flask',
          'Framework :: Pylons',
          'Framework :: Pyramid',
          'Framework :: TurboGears',
          'Framework :: Twisted',
          'Framework :: Zope2',
          'Framework :: Zope3',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
      ],
      author='Marcin Lulek',
      author_email='info@webreactor.eu',
      license='BSD',
      zip_safe=True,
      packages=find_packages(),
      include_package_data=True,
      package_data={
          '': ['*.txt', '*.rst', '*.ini'],
          'appenlight_client': ['templates/*.ini'],
      },
      install_requires=[
          'webob',
          'requests',
          'six'
      ],
      entry_points="""
      [paste.filter_app_factory]
      main = appenlight_client.client:make_appenlight_middleware
      appenlight = appenlight_client.client:make_appenlight_middleware
      [console_scripts]
      appenlight_client = appenlight_client.cli:cli_start
      """,
      test_suite='appenlight_client.tests',
      use_2to3=True,
      se_2to3_exclude_fixers=['lib2to3.fixes.next', 'lib2to3.fixes.fix_import']
      )
