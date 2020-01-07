from __future__ import absolute_import
import os
import subprocess
import uuid
from textwrap import dedent

from verst.pants.docker.docker_python_bundle_task import DockerPythonBundleTask
from verst.pants.docker.target import DockerPythonTarget
from verst_test.pants.docker.docker_bundle_test_mixin import DockerBundleTestMixin

from pants.backend.python.register import build_file_aliases as register_python
from pants.build_graph.address import Address
from pants_test.tasks.task_test_base import TaskTestBase

from pants.backend.python.tasks.python_binary_create import PythonBinaryCreate
from pants.base.run_info import RunInfo
from six.moves import map


class InterpreterCacheTestMixin(object):
  """A mixin to allow tests to use the "real" interpreter cache.
  This is so each test doesn't waste huge amounts of time recreating the cache on each run.
  Note: Must be mixed in to a subclass of BaseTest.
  
  Copied from pantsbuild/pants because it's not exposed in testinfra
  TODO(todd): include it
  """

  def setUp(self):  # noqa: T002
    super(InterpreterCacheTestMixin, self).setUp()

    # It would be nice to get the location of the real interpreter cache from PythonSetup,
    # but unfortunately real subsystems aren't available here (for example, we have no access
    # to the enclosing pants instance's options), so we have to hard-code it.
    python_setup_workdir = os.path.join(self.real_build_root, '.pants.d', 'python-setup')
    self.set_options_for_scope(
      'python-setup',
      interpreter_cache_dir=os.path.join(python_setup_workdir, 'interpreters'),
      chroot_cache_dir=os.path.join(python_setup_workdir, 'chroots'))


class PythonTaskTestBase(InterpreterCacheTestMixin, TaskTestBase):
  """
  Copied from pantsbuild/pants because it's not exposed in testinfra
  TODO(todd): include it

  :API: public
  """

  @property
  def alias_groups(self):
    """
    :API: public
    """
    return register_python()

  def create_python_library(self, relpath, name, source_contents_map=None,
                            dependencies=(), provides=None):
    """
    :API: public
    """
    sources = None if source_contents_map is None else ['__init__.py'] + list(source_contents_map.keys())
    sources_strs = ["'{0}'".format(s) for s in sources] if sources else None
    self.create_file(relpath=self.build_path(relpath), contents=dedent("""
    python_library(
      name='{name}',
      {sources_clause}
      dependencies=[
        {dependencies}
      ],
      {provides_clause}
    )
    """).format(
      name=name,
      sources_clause='sources=[{0}],'.format(','.join(sources_strs)) if sources_strs else '',
      dependencies=','.join(map(repr, dependencies)),
      provides_clause='provides={0},'.format(provides) if provides else ''))
    if source_contents_map:
      self.create_file(relpath=os.path.join(relpath, '__init__.py'))
      for source, contents in source_contents_map.items():
        self.create_file(relpath=os.path.join(relpath, source), contents=contents)
    return self.target(Address(relpath, name).spec)

  def create_python_binary(self, relpath, name, entry_point, dependencies=(), provides=None):
    """
    :API: public
    """
    self.create_file(relpath=self.build_path(relpath), contents=dedent("""
    python_binary(
      name='{name}',
      entry_point='{entry_point}',
      dependencies=[
        {dependencies}
      ],
      {provides_clause}
    )
    """).format(name=name, entry_point=entry_point, dependencies=','.join(map(repr, dependencies)),
                provides_clause='provides={0},'.format(provides) if provides else ''))
    return self.target(Address(relpath, name).spec)

  def create_python_requirement_library(self, relpath, name, requirements):
    """
    :API: public
    """
    def make_requirement(req):
      return 'python_requirement("{}")'.format(req)

    self.create_file(relpath=self.build_path(relpath), contents=dedent("""
    python_requirement_library(
      name='{name}',
      requirements=[
        {requirements}
      ]
    )
    """).format(name=name, requirements=','.join(map(make_requirement, requirements))))
    return self.target(Address(relpath, name).spec)


class TestDockerPythonBundleTask(PythonTaskTestBase, DockerBundleTestMixin):
  @classmethod
  def task_type(cls):
    return DockerPythonBundleTask

  def test_python_docker_image(self):
    expected_image_name = 'test-image-%s' % uuid.uuid4()
    expected_image = expected_image_name + ':foo-bar'

    self.create_python_library('src/python/lib', 'lib', {'lib.py': dedent("""
    import os
    def main():
      os.getcwd()
    """)})

    binary = self.create_python_binary(
      'src/python/bin', 'bin', 'lib.lib:main',
      dependencies=['//src/python/lib'])

    docker_target = self.make_target(
      spec='//bar:bar-image',
      target_type=DockerPythonTarget,
      image_name=expected_image_name,
      image_tag='foo-bar',
      base_image='scratch',
      dependencies=[binary])

    binary_create_type = self.synthesize_task_subtype(PythonBinaryCreate, 'bc_scope')

    task_context = self.context(
      for_task_types=[binary_create_type],
      target_roots=[docker_target]
    )

    run_info_dir = os.path.join(self.pants_workdir, self.options_scope, 'test/info')
    task_context.run_tracker.run_info = RunInfo(run_info_dir)
    test_task = self.create_task(task_context)

    binary_create_type(task_context, os.path.join(self.pants_workdir, 'bc')).execute()

    try:
      test_task.execute()

      with self.parse_tar(task_context, docker_target, expected_image) as tar:
        self.assertIn('manifest.json', tar.getnames())
        # TODO test more properties if we can assure it's hermetic somehow
    finally:
      subprocess.call(['docker', 'rmi', expected_image])
