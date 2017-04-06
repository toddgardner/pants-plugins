import os

from .docker_base_task import DockerBaseTask
from .target import DockerTargetBase

from pants.base.workunit import WorkUnitLabel
from pants.console import stty_utils


class DockerRun(DockerBaseTask):
  @classmethod
  def register_options(cls, register):
    super(DockerRun, cls).register_options(register)
    register('--inherit-env', type=bool, default=False,
             help='Export your current environment to the docker image')
    register('--opts',
             type=list,
             help='Docker options to pass.')
    register('--command', help='Command to run.')
    register('--args',
             type=list,
             help='Args to pass after command.')

  @classmethod
  def supports_passthru_args(cls):
    return True

  @classmethod
  def prepare(cls, options, round_manager):
    super(DockerRun, cls).prepare(options, round_manager)

  @classmethod
  def implementation_version(cls):
    return super(DockerRun, cls).implementation_version() + [('DockerRun', 1)]

  def execute(self):
    target = self.require_single_root_target()
    if not isinstance(target, DockerTargetBase):
      return
    cmd = ['docker', 'run']

    if self.get_options().inherit_env:
      for k, v in os.environ.items():
        cmd.extend(['-e', "{0}={1}".format(k, v)])

    opts = self.get_options().opts
    if opts:
      cmd.extend(opts)

    cmd.append(self._image_name(target))

    command = self.get_options().command
    if command:
      cmd.append(command)

    args = self.get_options().args + self.get_passthru_args()
    if args:
      cmd.extend(args)

    with self.context.new_workunit(name='run', labels=[WorkUnitLabel.RUN]) as workunit:
      self.context.release_lock()
      with stty_utils.preserve_stty_settings():
        self._run_docker_command(workunit, cmd)
