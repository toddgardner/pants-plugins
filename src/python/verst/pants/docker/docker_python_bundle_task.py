import logging
import os
import shutil

from .docker_base_task import DockerBaseBundleTask
from .target import DockerPythonTarget

from pants.backend.python.targets.python_binary import PythonBinary
from pants.base.exceptions import TaskError

logger = logging.getLogger(__name__)


DOCKERFILE = '''
FROM {baseimage}
COPY ./app.pex /app/bin/app.pex
CMD ["/app/bin/app.pex"]
'''


class DockerPythonBundleTask(DockerBaseBundleTask):
  @classmethod
  def register_options(cls, register):
    super(DockerPythonBundleTask, cls).register_options(register)
    register('--base-image', type=str,
             default='python:2.7',
             help='Base docker image to build python images')

  @classmethod
  def prepare(cls, options, round_manager):
    super(DockerPythonBundleTask, cls).prepare(options, round_manager)
    round_manager.require_data('pex_archives')

  @classmethod
  def implementation_version(cls):
    return (super(DockerPythonBundleTask, cls).implementation_version() +
            [('DockerPythonBundleTask', 1)])

  def is_docker(self, target):
    return isinstance(target, DockerPythonTarget)

  def _check_dependency_type(self, dependency):
    if not isinstance(dependency, PythonBinary):
      raise TaskError('docker_python_image needs a python_binary as a dependency')

  def _prepare_directory(self, target, dependency, tmpdir):
    archive_mapping = self.context.products.get('pex_archives').get(dependency)
    basedir, paths = archive_mapping.items()[0]
    path = paths[0]
    archive_path = os.path.join(basedir, path)

    shutil.copy(archive_path, os.path.join(tmpdir, 'app.pex'))

    base_image = self._base_image(target)
    with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as docker_file:
      docker_file.write(DOCKERFILE.format(baseimage=base_image))
