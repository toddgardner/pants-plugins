from __future__ import absolute_import
from pants.build_graph.target import Target
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField

class YoyoTarget(Target):
  def __init__(self,
               db_string=None,
               prod_db_envvar='POSTGRES_URL',
               payload=None, **kwargs):
    payload = payload or Payload()
    payload.add_fields({
      "db_string": PrimitiveField(db_string),
      "prod_db_envvar": PrimitiveField(prod_db_envvar)
    })

    super(YoyoTarget, self).__init__(payload=payload, **kwargs)
