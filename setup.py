from setuptools import setup, find_packages


setup(name='appenlight_client',
      version='0.6.9',
      description='Client for Appenlight reporting - supporting WSGI and django (http://appenlight.com)',
      classifiers=[
          'Intended Audience :: Developers',
          'License :: DFSG approved',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
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
          'appenlight_client': ['templates/*.ini'],
      },
      install_requires=[
          "webob",
          "requests"
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
