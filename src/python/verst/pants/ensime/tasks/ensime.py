from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import pkgutil
from collections import defaultdict
from collections import namedtuple
from twitter.common.collections import OrderedSet

from pants.backend.project_info.tasks.ide_gen import IdeGen
from pants.base.build_environment import get_buildroot
from pants.build_graph.address import Address
from pants.backend.jvm.targets.java_library import JavaLibrary
from pants.backend.jvm.targets.exclude import Exclude
from pants.base.generator import Generator, TemplateData
from pants.util.dirutil import safe_open
from pants.backend.jvm.subsystems import scala_platform
from pants.backend.jvm.subsystems.jvm_platform import JvmPlatform

_TEMPLATE_BASEDIR = os.path.join('templates', 'ensime')
_DEFAULT_PROJECT_DIR = './.pants.d/ensime/project'

SourceBase = namedtuple("SourceBase", "id path")

class EnsimeGen(IdeGen):
  """Create an Ensime project from the given targets."""

  @classmethod
  def register_options(cls, register):
    register('--excluded-deps', type=list, advanced=True,
             help='Exclude these targets from dependency resolution during workspace generation')
    super(EnsimeGen, cls).register_options(register)

  def __init__(self, *args, **kwargs):
    super(EnsimeGen, self).__init__(*args, **kwargs)

    self.project_template = os.path.join(_TEMPLATE_BASEDIR, 'ensime.mustache')
    self.project_filename = os.path.join(self.cwd, '.ensime')
    self.ensime_output_dir = os.path.join(self.gen_project_workdir, 'out')

  def resolve_jars(self, targets):
    excluded_targets = set()

    for exclusion in self.get_options().excluded_deps:
      for target in self.context.resolve(exclusion):
        excluded_targets.add(target)

    synthetic_target = self.context.add_new_target(
      address=Address('', 'exlusions'),
      target_type=JavaLibrary,
      dependencies=list(),
      sources=list(),
      excludes=[]
    )
    filtered_targets = [target for target in targets if not target in excluded_targets] + [synthetic_target]

    return super(EnsimeGen, self).resolve_jars(filtered_targets)

  def generate_project(self, project):
    def linked_folder_id(source_set):
      return source_set.source_base.replace(os.path.sep, '.')

    def base_path(source_set):
      return os.path.join(source_set.root_dir, source_set.source_base, source_set.path)

    def create_source_base_template(source_set):
      source_base = base_path(source_set)
      return SourceBase(
        id=linked_folder_id(source_set),
        path=source_base
      )

    source_sets = project.sources[:]
    if project.has_python:
      source_sets.extend(project.py_sources)

    source_bases = frozenset(map(create_source_base_template, source_sets))

    libs = []

    def add_jarlibs(classpath_entries):
      for classpath_entry in classpath_entries:
        libs.append((classpath_entry.jar, classpath_entry.source_jar))
    add_jarlibs(project.internal_jars)
    add_jarlibs(project.external_jars)
    scala_full_version = scala_platform.scala_build_info[self.context.options['scala-platform']['version']].full_version
    scala = TemplateData(
      language_level=scala_full_version,
      compiler_classpath=project.scala_compiler_classpath
    )

    outdir = os.path.abspath(self.ensime_output_dir)
    if not os.path.exists(outdir):
      os.makedirs(outdir)

    java_platform = JvmPlatform.global_instance().default_platform
    jdk_home = JvmPlatform.preferred_jvm_distribution([java_platform], strict=True).home

    configured_project = TemplateData(
      name=self.project_name,
      java_home=jdk_home,
      scala=scala,
      source_bases=source_bases,
      has_tests=project.has_tests,
      internal_jars=[cp_entry.jar for cp_entry in project.internal_jars],
      internal_source_jars=[cp_entry.source_jar for cp_entry in project.internal_jars
                            if cp_entry.source_jar],
      external_jars=[cp_entry.jar for cp_entry in project.external_jars],
      external_javadoc_jars=[cp_entry.javadoc_jar for cp_entry in project.external_jars
                             if cp_entry.javadoc_jar],
      external_source_jars=[cp_entry.source_jar for cp_entry in project.external_jars
                            if cp_entry.source_jar],
      libs=libs,
      outdir=os.path.relpath(outdir, get_buildroot()),
      root_dir=get_buildroot(),
      cache_dir=os.path.join(self.cwd, '.ensime_cache')
    )

    def apply_template(output_path, template_relpath, **template_data):
      with safe_open(output_path, 'w') as output:
        Generator(pkgutil.get_data(__name__, template_relpath), **template_data).write(output)

    apply_template(self.project_filename, self.project_template, project=configured_project)
    print('\nGenerated ensime project at {}{}'.format(self.gen_project_workdir, os.sep))
