from pants.base.exceptions import TargetDefinitionException
from pants.build_graph.resources import Resources
from pants.base.payload import Payload
from pants.util.memo import memoized_property
from pants.base.payload_field import PrimitiveField

class AbsoluteResources(Resources):
  def __init__(self, target_base=None, payload=None, *args, **kwargs):
    payload = payload or Payload()
    super(AbsoluteResources, self).__init__(payload=payload, *args, **kwargs)

  @memoized_property
  def target_base(self):
    return self.address.spec_path
