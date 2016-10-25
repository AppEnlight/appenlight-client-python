import appenlight_client
from setuptools import setup, find_packages

setup(name='appenlight_client',
      version=appenlight_client.__version__,
      description='Client for AppEnlight reporting - WSGI applications and django monitoring (http://getappenlight.com)',
      long_description=open("README.rst").read(),
      keywords = "monitoring, wsgi, django, flask, pylons, pyramid, debugging, debug, reporting, errors, errormator, appenlight client, sentry alternative",
      classifiers=[
          'Classifier: Development Status :: 5 - Production/Stable',
          'Classifier: Environment :: Web Environment',
          'Classifier: Framework :: BFG',
          'Classifier: Framework :: CherryPy',
          'Classifier: Framework :: Django',
          'Classifier: Framework :: Flask',
          'Classifier: Framework :: Pylons',
          'Classifier: Framework :: Pyramid',
          'Classifier: Framework :: TurboGears',
          'Classifier: Framework :: Twisted',
          'Classifier: Framework :: Zope2',
          'Classifier: Framework :: Zope3',
          'Classifier: Intended Audience :: Developers',
          'Classifier: License :: OSI Approved :: BSD License',
          'Classifier: Programming Language :: Python :: 2.6',
          'Classifier: Programming Language :: Python :: 2.7',
          'Classifier: Programming Language :: Python :: 3.2',
          'Classifier: Programming Language :: Python :: 3.3',
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
