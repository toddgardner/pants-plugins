from pants.build_graph.build_file_aliases import BuildFileAliases
from pants.goal.task_registrar import TaskRegistrar as task
from .task import SlickTask
from .target import SlickGenTarget

def build_file_aliases():
  return BuildFileAliases(
    targets={
      'slick_gen': SlickGenTarget,
    },
  )

def register_goals():
  task(name='slick-gen', action=SlickTask).install()
