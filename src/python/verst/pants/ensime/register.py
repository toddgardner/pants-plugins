from __future__ import absolute_import
from pants.goal.task_registrar import TaskRegistrar as task
from verst.pants.plugins.ensime.tasks.ensime import EnsimeGen

def register_goals():
  task(name='ensime-verst', action=EnsimeGen).install()
