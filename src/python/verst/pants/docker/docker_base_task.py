import logging
import os
import stat
import subprocess

from pants.base.exceptions import TaskError
from pants.base.workunit import WorkUnit, WorkUnitLabel
from pants.task.task import Task
from pants.util.contextutil import temporary_dir

logger = logging.getLogger(__name__)


class DockerBaseTask(Task):
  def _run_docker_command(self, workunit, cmdline):
    stderr = workunit.output('stderr') if workunit else None
    logger.debug('Docker command starting: {0}', ' '.join(cmdline))
    try:
      process = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=stderr)
      logger.debug('Docker command started with pid [{0}]', process.pid)
    except OSError as e:
      if workunit:
        workunit.set_outcome(WorkUnit.FAILURE)
      raise TaskError('Docker failed to execute {cmdline}: {error}'.format(
        cmdline=' '.join(cmdline), error=e
      ))

    stdout, _ = process.communicate()

    if workunit:
      workunit.output('stdout').write(stdout)
      workunit.set_outcome(WorkUnit.FAILURE if process.returncode else WorkUnit.SUCCESS)
    if process.returncode:
      raise TaskError('Docker failed to run {cmdline}'.format(cmdline=' '.join(cmdline)))
    logger.debug('Docker command finished')

  def _image_name(self, target):
    return "{}:{}".format(target.image_name, target.image_tag)


class DockerBaseBundleTask(DockerBaseTask):
  @property
  def create_target_dirs(self):
    return True

  @classmethod
  def product_types(cls):
    return ['docker_image']

  def _base_image(self, target):
    return target.base_image or self.get_options().base_image

  def execute(self):
    targets = self.context.targets(self.is_docker)

    # Check for duplicate binary names, since we write the pexes to <dist>/<name>.pex.
    names = {}
    for image in targets:
      name = self._image_name(image)
      if name in names:
        raise TaskError('Cannot build two docker images with the same name in a single invocation. '
                        '{} and {} both have the name {}.'.format(image, names[name], name))
      names[name] = image

    with self.invalidated(targets) as invalidation_check:
      for vt in invalidation_check.all_vts:
        if vt.valid:
          continue
        self._build_docker_image(vt.target)
        self._save_results(vt.target, vt.results_dir)
        docker_image = self.context.products.get('docker_image')
        docker_image.add(vt.target, vt.results_dir).append('docker_image_name')

  def _build_docker_image(self, target):
    with temporary_dir() as tmpdir:
      if len(target.dependencies) != 1:
        raise TaskError('Can only build a docker image out of a dependency')
      dependency = target.dependencies[0]
      self._check_dependency_type(dependency)
      self._prepare_directory(target, dependency, tmpdir)
      self._run_docker_build(target, tmpdir)

  def _run_docker_build(self, target, tmpdir):
    with self.context.new_workunit(name='create-bundle', labels=[WorkUnitLabel.TASK]) as workunit:
      self._run_docker_command(
        workunit, ['docker', 'build', '-t', self._image_name(target), tmpdir])

  def _save_results(self, target, results_dir):
    with open(os.path.join(results_dir, 'docker_image_name'), 'w') as f:
      f.write(self._image_name(target))

  @staticmethod
  def _make_executable(path):
    mode = os.stat(path).st_mode
    mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(path, mode)
