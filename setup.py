from setuptools import setup, find_packages


setup(name='errormator_client',
      version='0.3.11',
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
      zip_safe=True,
      packages=find_packages(),
      install_requires=[
          "webob"
      ],
      entry_points="""
      [paste.filter_app_factory]
      main = errormator_client.client:make_errormator_middleware
      errormator = errormator_client.client:make_errormator_middleware
      """,
      )
