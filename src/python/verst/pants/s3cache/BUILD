python_library(
  sources=globs('*.py'),
  dependencies=[
    '3rdparty/python:boto3',
    '3rdparty/python:pantsbuild.pants',
    '3rdparty/python:pyjavaproperties',
    '3rdparty/python:six',
  ],
)

python_library(
  name='s3cache_packaged',
  sources=[],
  dependencies=[
    ':s3cache',
  ],
  provides=setup_py(
    name='verst.pants.s3cache',
    maintainer="Todd Gardner",
    maintainer_email="todd.gardner@gmail.com",
	version='1.4.0',
	url='https://github.com/toddgardner/pants-plugins',
	description='An S3 caching backend for pants artifact cache',
	license='MIT',
	long_description='An S3 caching backend for pants artifact cache',
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
        'build_file_aliases = verst.pants.s3cache.register:build_file_aliases',
        'register_goals = verst.pants.s3cache.register:register_goals',
        'global_subsystems = verst.pants.s3cache.register:global_subsystems',
      ]
    },
  )
)
