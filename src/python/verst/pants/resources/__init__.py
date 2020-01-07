from __future__ import absolute_import
import os
import re

from pants.base.build_environment import get_buildroot

def resource_names_and_directories(path):
  # Walk the subdirectories under me/, and create a resources target for each
  # directory that contains at least one regular file
  for dirpath, dirnames, filenames in os.walk(os.path.join(get_buildroot(), path)):
    if not filenames:
      continue
    local_path = dirpath[len(os.path.join(get_buildroot(), path)):]
    name = re.sub("/", "-", local_path)
    yield name, local_path
