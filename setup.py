from setuptools import setup, find_packages


setup(name='errormator_client',
      version='0.5',
      description='Client for Errormator reporting - supporting WSGI and django (http://errormator.com)',
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
      zip_safe=True,
      packages=find_packages(),
      include_package_data=True,
      package_data={
        '': ['*.txt', '*.rst', '*.ini'],
        'errormator_client': ['templates/*.ini'],
        },
      install_requires=[
          "webob",
          "decorator"
      ],
      entry_points="""
      [paste.filter_app_factory]
      main = errormator_client.client:make_errormator_middleware
      errormator = errormator_client.client:make_errormator_middleware
      [console_scripts]
      errormator_client = errormator_client.cli:cli_start
      """,
      )
