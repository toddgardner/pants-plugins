from .docker_base_task import DockerBaseTask
from .target import DockerTargetBase

from pants.base.workunit import WorkUnitLabel


class DockerPublish(DockerBaseTask):
  @classmethod
  def prepare(cls, options, round_manager):
    super(DockerPublish, cls).prepare(options, round_manager)
    round_manager.require_data('docker_image')

  @classmethod
  def implementation_version(cls):
    return super(DockerPublish, cls).implementation_version() + [('DockerPublish', 1)]

  def is_docker(self, target):
    return isinstance(target, DockerTargetBase)

  def execute(self):
    targets = self.context.targets(self.is_docker)

    with self.invalidated(targets) as invalidation_check:
      for vt in invalidation_check.all_vts:
        if vt.valid:
          continue
        self._publish_docker_image(vt.target)

  def _publish_docker_image(self, target):
    with self.context.new_workunit(name='push', labels=[WorkUnitLabel.TASK]) as workunit:
      cmd = ['docker', 'push', self._image_name(target)]
      self._run_docker_command(workunit, cmd)
