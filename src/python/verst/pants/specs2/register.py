from __future__ import absolute_import
from pants.build_graph.build_file_aliases import BuildFileAliases
from pants.build_graph.target import Target
from pants.goal.task_registrar import TaskRegistrar as task
from .task import Specs2Run
from .target import Specs2Tests

def build_file_aliases():
  return BuildFileAliases(
    targets={
      'specs2_tests': Specs2Tests,
    },
  )

def register_goals():
  task(name='specs2', action=Specs2Run).install('test')
