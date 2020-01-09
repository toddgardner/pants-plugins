from __future__ import absolute_import
from pants.build_graph.build_file_aliases import BuildFileAliases
from pants.goal.task_registrar import TaskRegistrar as task
from .task import YoyoTask
from .target import YoyoTarget

def build_file_aliases():
  return BuildFileAliases(
    targets={
      'yoyo': YoyoTarget,
    },
  )

def register_goals():
  task(name='migrate', action=YoyoTask).install()
