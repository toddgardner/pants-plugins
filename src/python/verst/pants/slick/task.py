from pants.backend.jvm.tasks.nailgun_task import NailgunTask
from .target import SlickGenTarget
import os

class SlickTask(NailgunTask):
    """Generate the scala bindings for SLICK. Operates on slick_gen targets"""

    @classmethod
    def register_options(cls, register):
        super(SlickTask, cls).register_options(register)
        cls.register_jvm_tool(register, 'slick-gen')

    @classmethod
    def prepare(cls, options, round_manager):
      super(SlickTask, cls).prepare(options, round_manager)
      round_manager.require_data('yoyo_migrations')

    def is_slick(self, target):
        return isinstance(target, SlickGenTarget)

    def execute(self):
        targets = self.context.targets(self.is_slick)
        for target in targets:
            return_code = self.gen(target)
            if return_code != 0:
                return return_code
        return 0


    def gen(self, target):
        classpath = self.tool_classpath('slick-gen')
        args = ['--config-entry', target.payload.config_entry,
                '--driver', target.payload.driver_class,
                '--exclude-tables', ','.join(target.payload.excluded_tables),
                '--config-file', self.extract_absolute_conf(target),
                '--output-dir', target.target_base,
                '--package', self.implied_package(target)]
        if target.payload.schema:
            map(args.append, ['--schema', target.payload.schema])
        return self.runjava(classpath = classpath,
                            main = 'co.verst.slick.SlickGen',
                            args = args)

    def extract_absolute_conf(self, target):
        return os.path.abspath(os.path.join(target.address.spec_path, target.payload.config_file))

    def implied_package(self, target):
        abs_spec_path = os.path.abspath(target.address.spec_path)
        src_root_relative_path = os.path.relpath(abs_spec_path, target.target_base)
        return '.'.join(src_root_relative_path.split('/'))
