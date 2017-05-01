from pants.backend.jvm.tasks.scalastyle import Scalastyle
from pants.goal.task_registrar import TaskRegistrar as task
from pants.base.exceptions import TaskError

class SoftErrorScalastyle(Scalastyle):
  @classmethod
  def register_options(cls, register):
    super(SoftErrorScalastyle, cls).register_options(register)
    register('--soft-error', type=bool, fingerprint=True, default=False, help='Run scalastyle, but ignore failures')

  def execute(self):
    try:
      super(SoftErrorScalastyle, self).execute()
    except TaskError:
      if not self.get_options().soft_error:
        raise

def register_goals():
  task(name='scalastyle', action=SoftErrorScalastyle).install('compile')
