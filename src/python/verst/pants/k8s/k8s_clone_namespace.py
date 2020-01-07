from __future__ import absolute_import
from pants.base.exceptions import TaskError
from pants.base.build_environment import get_scm
from pants.task.task import Task
from pants.base.workunit import WorkUnit, WorkUnitLabel

from pants.util.contextutil import temporary_dir

import os
import stat
import subprocess

import logging
import pystache
from kubernetes import config, client

logger = logging.getLogger(__name__)
CLUSTER_SPECIFIC_METADATA = [
  'creationTimestamp',
  'resourceVersion',
  'uid',
  'selfLink']

class K8SCloneNamespace(Task):
  @classmethod
  def register_options(cls, register):
    branch = get_scm().branch_name
    register('--namespace', type=str, default=branch,
             help='Namespace to create.')
    super(K8SCloneNamespace, cls).register_options(register)

  @property
  def new_namespace(self):
    return self.get_options().namespace

  def execute(self):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    beta = client.ExtensionsV1beta1Api()
    # TODO: Make idempotent!
    self.create_namespace(v1)
    self.clone_configmaps(v1)
    self.clone_services(v1)
    self.clone_secrets(v1)
    self.clone_deployments(beta)

  def create_namespace(self, k8s):
    found = False
    for ns in k8s.list_namespace().items:
      found = found or ns.metadata.name == self.new_namespace
    if not found:
      k8s.create_namespace({'metadata': {'name': self.new_namespace}})


  def clone_services(self, k8s):
    for service in k8s.list_namespaced_service('devo').items:
      if service.spec.type == 'NodePort':
        logger.warning('Ignoring NodePort service %s' % service.metadata.name)
        continue
      service.metadata = { 'name': service.metadata.name, 'namespace': self.new_namespace }
      service.spec.cluster_ip = None
      k8s.create_namespaced_service(self.new_namespace, service)

  def clone_secrets(self, k8s):
    for secret in k8s.list_namespaced_secret('devo').items:
      if secret.type != 'Opaque':
        continue
      secret.metadata = { 'name': secret.metadata.name, 'namespace': self.new_namespace }
      k8s.create_namespaced_secret(self.new_namespace, secret)

  def clone_deployments(self, k8s):
    for deploy in k8s.list_namespaced_deployment('devo').items:
      deploy.metadata = { 'name': deploy.metadata.name, 'labels': deploy.metadata.labels, 'namespace': self.new_namespace }
      deploy.status = {}
      deploy.spec.template.metadata.creation_timestamp = None
      k8s.create_namespaced_deployment(self.new_namespace, deploy)

  def clone_configmaps(self, k8s):
    for configmap in k8s.list_namespaced_config_map('devo').items:
      configmap.metadata = { 'name': configmap.metadata.name, 'namespace': self.new_namespace }
      k8s.create_namespaced_config_map(self.new_namespace, configmap)


  def rinse_metadata(self, obj):
    meta = obj.metadata.to_dict()
    meta['namespace'] = self.new_namespace
    for attr in CLUSTER_SPECIFIC_METADATA:
      meta.pop(attr, None)
    obj.metadata = meta
