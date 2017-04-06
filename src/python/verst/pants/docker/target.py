from pants.base.build_environment import get_scm
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField
from pants.build_graph.target import Target


class DockerTargetBase(Target):
  def __init__(self, address=None, payload=None, image_name=None, image_tag=None, **kwargs):
    payload = payload or Payload()
    payload.add_fields({
      'image_name': PrimitiveField(image_name),
      'image_tag': PrimitiveField('c' + get_scm().commit_id)
    })
    self.image_name = image_name
    self.image_tag = image_tag
    super(DockerTargetBase, self).__init__(address=address, payload=payload, **kwargs)


class DockerBundleTarget(DockerTargetBase):
  def __init__(self, base_image=None, payload=None, **kwargs):
    payload = payload or Payload()
    payload.add_fields({
      'base_image': PrimitiveField(base_image)
    })
    self.base_image = base_image
    super(DockerBundleTarget, self).__init__(payload=payload, **kwargs)


class DockerJvmAppTarget(DockerBundleTarget):
  pass


class DockerPythonTarget(DockerBundleTarget):
  pass
