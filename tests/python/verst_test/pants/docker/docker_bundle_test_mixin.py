from contextlib import contextmanager
import os
import subprocess

from pants.util.contextutil import open_tar, temporary_dir


class DockerBundleTestMixin(object):
  @contextmanager
  def parse_tar(self, context, target, expected_image):
    docker_image_products = context.products.get('docker_image')
    self.assertIsNotNone(docker_image_products)
    product_data = docker_image_products.get(target)
    self.assertEqual(1, len(product_data))
    result_dir, result_keys = product_data.items()[0]
    self.assertEqual(['docker_image_name'], result_keys)
    image_name_file = os.path.join(result_dir, result_keys[0])
    with open(image_name_file, 'r') as f:
      result_image_name = f.read()
    self.assertEqual(expected_image, result_image_name)

    with temporary_dir() as result_td:
      result_tar = os.path.join(result_td, 'contents.tar')
      subprocess.check_call(['docker', 'save', '--output=' + result_tar, result_image_name])

      with open_tar(result_tar) as tar:
        yield tar