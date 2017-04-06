import fnmatch
import logging
import os
import shutil

from .docker_base_task import DockerBaseBundleTask
from .target import DockerJvmAppTarget

from pants.backend.jvm.targets.jvm_app import JvmApp
from pants.base.exceptions import TaskError

from pants.backend.jvm.subsystems.jvm_tool_mixin import JvmToolMixin


logger = logging.getLogger(__name__)

RUNSCRIPT = '''#!/bin/sh
exec java $JAVA_OPTS -jar /app/bin/bundle/{jar_name} "$@"
'''

REPLSCRIPT = '''#!/bin/sh
exec java $JAVA_OPTS -cp '/app/bin/bundle/libs/*' scala.tools.nsc.MainGenericRunner -usejavacp
'''

DOCKERFILE = '''FROM {base_image}
# Copy third party dependencies separately to help improve caching.
{third_party_libs}
{non_third_party_libs}
COPY ./bundle/{jar_name} /app/bin/bundle
COPY ./run.sh /app/bin
COPY ./repl.sh /app/bin

CMD ["/app/bin/run.sh"]
'''


def _any_matching_file(dir, pattern):
  for file in os.listdir(dir):
    if fnmatch.fnmatch(file, pattern):
      return True
  return False


class DockerJvmAppBundleTask(JvmToolMixin, DockerBaseBundleTask):
  @classmethod
  def prepare(cls, options, round_manager):
    super(DockerJvmAppBundleTask, cls).prepare(options, round_manager)
    round_manager.require_data('jvm_bundles')

  @classmethod
  def implementation_version(cls):
    return (super(DockerJvmAppBundleTask, cls).implementation_version() +
            [('DockerJvmAppBundleTask', 1)])

  def is_docker(self, target):
    return isinstance(target, DockerJvmAppTarget)

  def _check_dependency_type(self, dependency):
    if not isinstance(dependency, JvmApp):
      raise TaskError('docker_jvm_image needs a jvm_app as a dependency')

  def _prepare_directory(self, target, dependency, tmpdir):
    archive_mapping = self.context.products.get('jvm_bundles').get(dependency)
    basedir, paths = archive_mapping.items()[0]
    path = paths[0]
    archive_path = os.path.join(basedir, path)

    jar_name = dependency.binary.name + '.jar'
    bundle_dir = os.path.join(tmpdir, 'bundle')
    os.mkdir(bundle_dir)
    libs_dir = os.path.join(bundle_dir, 'libs')
    shutil.copytree(os.path.join(archive_path, 'libs'), libs_dir)
    shutil.copy(os.path.join(archive_path, jar_name), bundle_dir)

    if _any_matching_file(libs_dir, '3*'):
      third_party_copy = "COPY ./bundle/libs/3* /app/bin/bundle/libs/"
    else:
      third_party_copy = ''

    if _any_matching_file(libs_dir, '[!3]*'):
      non_third_party_copy = "COPY ./bundle/libs/[^3]* /app/bin/bundle/libs/"
    else:
      non_third_party_copy = ''

    base_image = self._base_image(target)
    with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as docker_file:
      docker_file.write(DOCKERFILE.format(
        base_image=base_image, jar_name=jar_name,
        third_party_libs=third_party_copy,
        non_third_party_libs=non_third_party_copy
      ))

    run_path = os.path.join(tmpdir, 'run.sh')
    with open(run_path, 'w') as run_script:
      run_script.write(RUNSCRIPT.format(jar_name=jar_name))
    self._make_executable(run_path)

    repl_path = os.path.join(tmpdir, 'repl.sh')
    with open(repl_path, 'w') as repl_script:
      repl_script.write(REPLSCRIPT)
    self._make_executable(repl_path)
