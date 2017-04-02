from .cache_setup import patch

from pants.build_graph.build_file_aliases import BuildFileAliases


def build_file_aliases():
  patch()
  return BuildFileAliases()


def register_goals():
  patch()


def global_subsystems():
  patch()
  return set()
