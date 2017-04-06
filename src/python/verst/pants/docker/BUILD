python_library(
  sources=globs('*.py'),
  dependencies=[
    '3rdparty/python:pantsbuild.pants',
  ],
)

python_library(
  name='docker_packaged',
  sources=[],
  dependencies=[
    ':docker',
  ],
  provides=setup_py(
    name='verst.pants.docker',
    maintainer="Todd Gardner",
    maintainer_email="todd.gardner@gmail.com",
	version='1.2.0',
	url='https://github.com/toddgardner/pants-plugins',
	description='A docker plugin for pants',
	license='MIT',
	long_description='A docker plugin for pants',
	classifiers=[
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Operating System :: MacOS :: MacOS X',
      'Operating System :: POSIX :: Linux',
      'Topic :: Software Development :: Build Tools'
     ],
    namespace_packages=['verst', 'verst.pants'],
    zip_safe=True,
    entry_points={
      'pantsbuild.plugin': [
        'build_file_aliases = verst.pants.docker.register:build_file_aliases',
        'register_goals = verst.pants.docker.register:register_goals',
      ]
    },
  )
)
