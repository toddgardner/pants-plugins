from pants.build_graph.build_file_aliases import BuildFileAliases
from .target import AbsoluteResources

def build_file_aliases():
  return BuildFileAliases(
    targets={
      'absolute_resources': AbsoluteResources,
    },
  )
