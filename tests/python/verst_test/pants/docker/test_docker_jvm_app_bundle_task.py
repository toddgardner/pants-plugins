from __future__ import absolute_import
import os
import subprocess
import uuid

from verst.pants.docker.docker_jvm_app_bundle_task import DockerJvmAppBundleTask
from verst.pants.docker.target import DockerJvmAppTarget
from verst_test.pants.docker.docker_bundle_test_mixin import DockerBundleTestMixin

from pants.backend.jvm.targets.jvm_app import JvmApp
from pants.backend.jvm.tasks.bundle_create import BundleCreate
from pants.backend.jvm.tasks.consolidate_classpath import ConsolidateClasspath
from pants.util.dirutil import safe_mkdir

from pants.backend.jvm.jar_dependency_utils import M2Coordinate, ResolvedJar
from pants.backend.jvm.targets.jvm_binary import JvmBinary
from pants.backend.jvm.tasks.classpath_products import ClasspathProducts
from pants.util.contextutil import open_zip
from pants_test.jvm.jvm_tool_task_test_base import JvmToolTaskTestBase


class JvmBinaryTaskTestBase(JvmToolTaskTestBase):
  """
  Copied from pantsbuild/pants because it's not exposed in testinfra
  TODO(todd): include ig.

  :API: public
  """

  def create_artifact(self, org, name, rev, classifier=None, ext=None, materialize=True):
    """
    :API: public
    :param string org: The maven dependency `groupId`.
    :param string name: The maven dependency `artifactId`.
    :param string rev: The maven dependency `version`.
    :param string classifier: The maven dependency `classifier`.
    :param string ext: There is no direct maven parallel, but the maven `packaging` value of the
                       depended-on artifact for simple cases, and in more complex cases the
                       extension of the artifact.  For example, 'bundle' packaging implies an
                       extension of 'jar'.  Defaults to 'jar'.
    :param bool materialize: `False` to populate the returned resolved_jar with a `pants_path` that
                             does not exist; defaults to `True` and `touch`es the `pants_path`.
    :returns: A resolved jar describing the artifact.
    :rtype: :class:`pants.java.jar.ResolvedJar`
    """
    coordinate = M2Coordinate(org=org, name=name, rev=rev, classifier=classifier, ext=ext)
    cache_path = 'not/a/real/cache/path'
    jar_name = coordinate.artifact_filename
    if materialize:
      pants_path = self.create_workdir_file(jar_name)
    else:
      pants_path = os.path.join(self.pants_workdir, jar_name)

    return ResolvedJar(coordinate=coordinate, cache_path=cache_path, pants_path=pants_path)

  def ensure_classpath_products(self, context):
    """Gets or creates the classpath products expected by `JvmBinaryTask`.
    :API: public
    :param context: The pants run context to get/create/associate classpath products with.
    :type context: :class:`pants.goal.context.Context`
    :returns: The classpath products associated with the given `context`
    :rtype: :class:`pants.backend.jvm.tasks.classpath_products.ClasspathProducts`
    """
    return context.products.get_data('runtime_classpath',
                                     init_func=ClasspathProducts.init_func(self.pants_workdir))


class TestDockerJvmBundleTask(JvmBinaryTaskTestBase, DockerBundleTestMixin):
  @classmethod
  def task_type(cls):
    return DockerJvmAppBundleTask

  def setUp(self):
    super(TestDockerJvmBundleTask, self).setUp()
    self.consolidate_classpath_type = self.synthesize_task_subtype(ConsolidateClasspath, 'cc_scope')
    self.bundle_create_type = self.synthesize_task_subtype(BundleCreate, 'bc_scope')

  def _create_context(self, target):
    self.test_context = self.context(
      for_task_types=[self.consolidate_classpath_type, self.bundle_create_type],
      target_roots=[target]
    )

    self.classpath_products = self.ensure_classpath_products(self.test_context)

  def _create_artifact(self, target, jarname):
    jar_artifact = self.create_artifact(org='org.example', name=jarname, rev='1.0.0')
    with open_zip(jar_artifact.pants_path, 'w') as jar:
      jar.writestr(jarname + '/Foo.class', '')
    self.classpath_products.add_jars_for_targets(targets=[target],
                                                 conf='default',
                                                 resolved_jars=[jar_artifact])

  def _execute(self):
    docker_jvm_bundle = self.prepare_execute(self.test_context)
    self.consolidate_classpath_type(
      self.test_context, os.path.join(self.pants_workdir, 'cc')).execute()
    self.bundle_create_type(self.test_context, os.path.join(self.pants_workdir, 'bc')).execute()
    docker_jvm_bundle.execute()

  def test_docker_image_products(self):
    expected_image_name = 'test-image-%s' % uuid.uuid4()
    expected_image = expected_image_name + ':foo-bar'
    binary_target = self.make_target(spec='//bar:bar-binary',
                                     target_type=JvmBinary,
                                     source='Bar.java')
    app_target = self.make_target(spec='//bar:bar-app',
                                  target_type=JvmApp,
                                  basename='foo-app',
                                  binary=':bar-binary')
    docker_target = self.make_target(spec='//bar:bar-image',
                                     target_type=DockerJvmAppTarget,
                                     image_name=expected_image_name,
                                     image_tag='foo-bar',
                                     base_image='scratch',
                                     dependencies=[app_target])

    safe_mkdir(os.path.join(self.build_root, 'bar'))
    with open(os.path.join(self.build_root, 'bar/Bar.java'), 'w') as f:
      f.write("""""")

    self._create_context(docker_target)

    self._create_artifact(binary_target, 'foo')

    self.add_to_runtime_classpath(
      self.test_context, binary_target, {'Bar.class': '', 'bar.txt': ''})

    try:
      self._execute()

      with self.parse_tar(self.test_context, docker_target, expected_image) as tar:
        self.assertIn('manifest.json', tar.getnames())
        # TODO test more properties if we can assure it's hermetic somehow
    finally:
      subprocess.call(['docker', 'rmi', expected_image])
