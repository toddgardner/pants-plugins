from .docker_jvm_app_bundle_task import DockerJvmAppBundleTask
from .docker_publish import DockerPublish
from .docker_python_bundle_task import DockerPythonBundleTask
from .docker_run import DockerRun
from .target import DockerJvmAppTarget, DockerPythonTarget

from pants.build_graph.build_file_aliases import BuildFileAliases
from pants.goal.task_registrar import TaskRegistrar as task


def build_file_aliases():
  return BuildFileAliases(
    targets={
      'docker_jvm_app_image': DockerJvmAppTarget,
      'docker_python_image': DockerPythonTarget
    }
  )


def register_goals():
  task(name='docker-jvm', action=DockerJvmAppBundleTask).install('bundle')
  task(name='docker-python', action=DockerPythonBundleTask).install('bundle')
  task(name='docker-publish', action=DockerPublish).install()
  task(name='docker', action=DockerRun).install('run')
