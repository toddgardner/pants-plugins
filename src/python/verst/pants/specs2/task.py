import os
from collections import defaultdict

from twitter.common.collections import OrderedSet

from pants.backend.jvm.argfile import safe_args
from pants.backend.jvm.subsystems.jvm_platform import JvmPlatform
from pants.backend.jvm.targets.java_tests import JavaTests as junit_tests
from pants.backend.jvm.tasks.junit_run import JUnitRun
from pants.base.exceptions import TestFailedTaskError
from pants.base.workunit import WorkUnitLabel
from pants.java.executor import SubprocessExecutor
from pants.util.argutil import ensure_arg, remove_arg
from pants.util.contextutil import environment_as
from pants.util.strutil import pluralize
from pants.util.xml_parser import XmlParser
from pants.base.exceptions import TaskError

from .target import Specs2Tests

class Specs2Run(JUnitRun):
  TEST_CLASS_PATTERN = r"(.*Spec)(?:\(.*\))?\s*extends"
  SPECS2_MAIN = "org.specs2.runner.files"

  @classmethod
  def register_options(cls, register):
    super(Specs2Run, cls).register_options(register)
    register('--args', type=list,
             help='Extra arguments to pass to specs2')
    register('--example', type=str, help='Only run test description matching this regex')
    register('--sequential', type=bool, default=False, help='Run tests sequentially')
    register('--show-times', type=bool, default=False, help='Print out the test times, I think')
    register('--file-pattern', type=str, help='Regex to select which tests to run.'
        ' The regex must match the entire class name to test in the first group')

    cls.register_jvm_tool(register, 'specs2', classpath_spec="3rdparty:specs2-core")
  def _test_target_filter(self):
    def target_filter(target):
      return isinstance(target, Specs2Tests)
    return target_filter

  def _run_tests(self, test_registry, output_dir, coverage=None):

    tests_by_properties = test_registry.index(
      lambda tgt: tgt.cwd if tgt.cwd is not None else self._working_dir,
      lambda tgt: tgt.platform)

    # the below will be None if not set, and we'll default back to runtime_classpath
    classpath_product = self.context.products.get_data('instrument_classpath')

    result = 0
    base_args = self.get_options().args
    for properties, tests in tests_by_properties.items():
      (cwd, platform) = properties
      for batch in self._partition(tests, test_registry):
        # Batches of test classes will likely exist within the same targets: dedupe them.
        relevant_targets = {test_registry.get_owning_target(t) for t in batch}
        if len(relevant_targets) > 1:
          raise "oops, should have only had one target"
        complete_classpath = OrderedSet()
        # TODO: Include specs2 on the classpath, in case the target doesn't
        complete_classpath.update(self.classpath(relevant_targets,
                                                 classpath_product=classpath_product))
        distribution = JvmPlatform.preferred_jvm_distribution([platform], self._strict_jvm_version)

        target_dir = list(relevant_targets)[0].address.spec_path
        args = base_args[:]
        opts = self.get_options()
        if opts.example:
          args.extend(["ex", opts.example])
        if opts.sequential:
          args.extend(['sequential', 'true'])
        if opts.show_times:
          args.extend(['showtimes', 'true'])
        file_pattern = opts.file_pattern or Specs2Run.TEST_CLASS_PATTERN
        if '(' not in file_pattern or ')' not in file_pattern:
          raise TaskError("Test regex must have a group.")
        args.extend([
          "junitxml",
          "console",
          "filesrunner.basepath", target_dir,
          "filesrunner.pattern", file_pattern,
          "junit.outdir", self.junit_xml_dir
        ])
        self.context.log.debug('CWD = {}'.format(cwd))
        self.context.log.debug('platform = {}'.format(platform))
        self.context.log.debug('targets = {}'.format(relevant_targets))
        self.context.log.debug('args = {}'.format(" ".join(args)))
        result += abs(self._spawn_and_wait(
          executor=SubprocessExecutor(distribution),
          distribution=distribution,
          classpath=complete_classpath,
          main=Specs2Run.SPECS2_MAIN,
          jvm_options=self.jvm_options,
          args=args,
          workunit_factory=self.context.new_workunit,
          workunit_name='run',
          workunit_labels=[WorkUnitLabel.TEST],
          cwd=cwd,
          synthetic_jar_dir=output_dir,
          create_synthetic_jar=self.synthetic_classpath,
        ))

        if result != 0 and self._fail_fast:
          break

    if result != 0:
      failed_targets_and_tests = self._get_failed_targets(test_registry, output_dir)
      failed_targets = sorted(failed_targets_and_tests, key=lambda target: target.address.spec)
      error_message_lines = []
      if self._failure_summary:
        for target in failed_targets:
          error_message_lines.append('\n{0}{1}'.format(' '*4, target.address.spec))
          for test in sorted(failed_targets_and_tests[target]):
            error_message_lines.append('{0}{1}'.format(' '*8, test))
      error_message_lines.append(
        '\njava {main} ... exited non-zero ({code}); {failed} failed {targets}.'
          .format(main=Specs2Run.SPECS2_MAIN, code=result, failed=len(failed_targets),
                  targets=pluralize(len(failed_targets), 'target'))
      )
      raise TestFailedTaskError('\n'.join(error_message_lines), failed_targets=list(failed_targets))

  def _get_failed_targets(self, test_registry, output_dir):
    """Override JunitRun's logic to find files generated by specs2
    """

    def get_test_filename(test_class_name):
      return os.path.join(self.workdir, '{0}.xml'.format(test_class_name.replace('$', '-')))

    xml_filenames_to_targets = defaultdict()
    for test, target in test_registry._test_to_target.items():
      if target is None:
        self.context.log.warn('Unknown target for test %{0}'.format(test))

      # Look for a *.xml file that matches the classname or a containing classname
      test_class_name = test.classname
      for _part in test_class_name.split('$'):
        filename = get_test_filename(test_class_name)
        if os.path.exists(filename):
          xml_filenames_to_targets[filename] = target
          break
        else:
          test_class_name = test_class_name.rsplit('$', 1)[0]

    failed_targets = defaultdict(set)
    for xml_filename, target in xml_filenames_to_targets.items():
      try:
        xml = XmlParser.from_file(xml_filename)
        failures = int(xml.get_attribute('testsuite', 'failures'))
        errors = int(xml.get_attribute('testsuite', 'errors'))

        if target and (failures or errors):
          for testcase in xml.parsed.getElementsByTagName('testcase'):
            test_failed = testcase.getElementsByTagName('failure')
            test_errored = testcase.getElementsByTagName('error')
            if test_failed or test_errored:
              failed_targets[target].add('{testclass}#{testname}'.format(
                  testclass=testcase.getAttribute('classname'),
                  testname=testcase.getAttribute('name'),
              ))
      except (XmlParser.XmlError, ValueError) as e:
        self.context.log.error('Error parsing test result file {0}: {1}'.format(xml_filename, e))

    return dict(failed_targets)

  def _partition(self, tests, test_registry):
    inverted = defaultdict(lambda: [])
    for test in tests:
      target = test_registry.get_owning_target(test)
      inverted[target].append(test)
    return inverted.values()

  @property
  def junit_xml_dir(self):
    if os.environ.has_key("CIRCLE_TEST_REPORTS"):
      return os.path.join(os.environ["CIRCLE_TEST_REPORTS"], "specs2")
    return super(Specs2Run, self).workdir
