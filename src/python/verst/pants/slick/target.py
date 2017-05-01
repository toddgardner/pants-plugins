from pants.build_graph.target import Target
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField
from pants.base.exceptions import TargetDefinitionException
from pants.backend.jvm.targets.jvm_binary import JvmBinary

class SlickGenTarget(Target):
  def __init__(self,
               config_file="application.conf",
               config_entry="",
               schema="",
               excluded_tables=[],
               driver_class="com.github.tminglei.slickpg.ExPostgresDriver",
               payload=None, **kwargs):
    payload = payload or Payload()
    payload.add_fields({
      "config_entry": PrimitiveField(config_entry),
      "schema": PrimitiveField(schema),
      "config_file": PrimitiveField(config_file),
      "driver_class": PrimitiveField(driver_class),
      "excluded_tables": PrimitiveField(excluded_tables),
    })

    super(SlickGenTarget, self).__init__(payload=payload, **kwargs)
