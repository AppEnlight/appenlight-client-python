from setuptools import setup


setup(name='errormator_client',
      version='0.2',
      description='Sample client for Errormator reporting',
      classifiers=[
          'Intended Audience :: Developers',
          'License :: DFSG approved',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries :: Python Modules',
          ],
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
