python_library(
  sources=globs('*.py'),
  dependencies=[
    '3rdparty/python:boto',
    '3rdparty/python:pantsbuild.pants',
    '3rdparty/python:pyjavaproperties',
    '3rdparty/python:six',
  ],
  provides=setup_py(
    name='verst.pants.s3_cache',
	version='1.0.0',
	description='An S3 caching backend for pants artifact cache',
	classifiers=[
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Operating System :: MacOS :: MacOS X',
      'Operating System :: POSIX :: Linux',
      'Programming Language :: Python',
      'Topic :: Software Development :: Build Tools'
     ],
     namespace_packages=['verst', 'verst.pants'],
     zip_safe=True
  )
)
