from pants.goal.task_registrar import TaskRegistrar as task
from .k8s_clone_namespace import K8SCloneNamespace

def register_goals():
  task(name='k8s-clone', action=K8SCloneNamespace).install()
