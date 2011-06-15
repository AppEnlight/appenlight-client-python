from setuptools import setup


setup(name='errormator_client',
      version='0.2',
      description=""" Sample client for Errormator reporting""",
      author='Marcin Lulek',
      author_email='info@webreactor.eu',
      license='BSD',
      py_modules=['errormator_client'],
      install_requires=[
          'Paste',
      ],
      entry_points="""
      [paste.filter_app_factory]
      error_catcher = errormator_client:make_catcher_middleware
      header_sniffer = errormator_client:make_sniffer_middleware
      """,
      )
