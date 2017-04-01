python_library(
  sources=globs('*.py'),
  dependencies=[
    '3rdparty/python:boto',
    '3rdparty/python:pantsbuild.pants',
    '3rdparty/python:pyjavaproperties',
    '3rdparty/python:six',
  ],
)

python_library(
  name='s3_cache_packaged',
  sources=[],
  dependencies=[
    ':s3_cache',
  ],
  provides=setup_py(
    name='verst.pants.s3_cache',
	version='1.0.0',
	url='https://github.com/toddgardner/pants-plugins',
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
    zip_safe=True,
    entry_points={
      'pantsbuild.plugin': [
        'build_file_aliases = verst.pants.s3_cache.register:build_file_aliases',
        'register_goals = verst.pants.s3_cache.register:register_goals',
        'global_subsystems = verst.pants.s3_cache.register:global_subsystems',
      ]
    },
  )
)
