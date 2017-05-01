import os
import logging
from pants.task.task import Task
from yoyo.scripts.main import main
from .target import YoyoTarget

logger = logging.getLogger(__name__)

class YoyoTask(Task):
    @classmethod
    def supports_passthru_args(cls):
        return True

    @classmethod
    def product_types(cls):
        return ['yoyo_migrations']

    def is_yoyo(self, target):
        return isinstance(target, YoyoTarget)

    def execute(self):
        targets = self.context.targets(self.is_yoyo)
        for target in targets:
            db_string = os.environ.get(target.payload.prod_db_envvar) or target.payload.db_string
            command_args = self.get_passthru_args() or ['apply']

            args = command_args + ['--database=%s' % db_string,
                                   os.path.abspath(target.address.spec_path)]
            logger.info('Running pants migrate %s' % ' '.join(args))
            main(args)


