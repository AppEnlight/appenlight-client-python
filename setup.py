from setuptools import setup, find_packages
import sys
setup(name='errormator_client',
      version='0.1',
      description=""" Sample client for Errormator reporting""",
      author='Marcin Lulek',
      author_email='info@webreactor.eu',
      license='BSD',
      py_modules = ['errormator_client'],
      entry_points="""
      [paste.filter_app_factory]
      error_catcher = errormator_client:make_catcher_middleware
      header_sniffer = errormator_client:make_sniffer_middleware
      """,
      )