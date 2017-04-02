# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import logging

from pants.cache.cache_setup import (CacheSetup, CacheSpecFormatError,
                                     LocalCacheSpecRequiredError, RemoteCacheSpecRequiredError,
                                     TooManyCacheSpecsError)
from pants.cache.local_artifact_cache import LocalArtifactCache
from pants.cache.restful_artifact_cache import RESTfulArtifactCache
from pants.subsystem.subsystem import Subsystem
from pants.task.task import Task
from pants.util.contextutil import temporary_dir
from pants_test.base_test import BaseTest

from verst.pants.s3cache.cache_setup import patch
from verst.pants.s3cache.s3cache import S3ArtifactCache


class DummyContext(object):
  log = logging.getLogger('DummyContext')  # noqa: T001


class DummyTask(Task):
  options_scope = 'dummy'  # noqa: T001

  context = DummyContext()  # noqa: T001

  @classmethod
  def subsystem_dependencies(cls):
    return super(DummyTask, cls).subsystem_dependencies() + (CacheSetup, )


class MockPinger(object):

  def __init__(self, hosts_to_times):
    self._hosts_to_times = hosts_to_times

  # Returns a fake ping time such that the last host is always the 'fastest'.
  def pings(self, hosts):
    return map(lambda host: (host, self._hosts_to_times.get(host, 9999)), hosts)


class TestCacheSetup(BaseTest):
  REMOTE_URI_1 = 'http://host1'
  REMOTE_URI_2 = 'https://host2:666'

  def setUp(self):
    super(TestCacheSetup, self).setUp()
    patch()

  def test_cache_spec_parsing(self):
    def mk_cache(spec):
      Subsystem.reset()
      self.set_options_for_scope(CacheSetup.subscope(DummyTask.options_scope),
                                 read_from=spec, compression=1)
      self.context(for_task_types=[DummyTask])  # Force option initialization.
      cache_factory = CacheSetup.create_cache_factory_for_task(
        DummyTask,
        pinger=MockPinger({'host1': 5, 'host2:666': 3, 'host3': 7}))
      return cache_factory.get_read_cache()

    def check(expected_type, spec):
      cache = mk_cache(spec)
      self.assertIsInstance(cache, expected_type)
      self.assertEquals(cache.artifact_root, self.pants_workdir)

    with temporary_dir() as tmpdir:
      cachedir = os.path.join(tmpdir, 'cachedir')  # Must be a real path, so we can safe_mkdir it.
      check(LocalArtifactCache, [cachedir])
      check(RESTfulArtifactCache, ['http://localhost/bar'])
      check(RESTfulArtifactCache, ['https://localhost/bar'])
      check(RESTfulArtifactCache, [cachedir, 'http://localhost/bar'])
      check(RESTfulArtifactCache, [cachedir, 'http://localhost/bar'])

      check(S3ArtifactCache, ['s3://some-bucket/bar'])
      check(S3ArtifactCache, [cachedir, 's3://some-bucket/bar'])

      with self.assertRaises(CacheSpecFormatError):
        mk_cache(['foo'])

      with self.assertRaises(CacheSpecFormatError):
        mk_cache(['../foo'])

      with self.assertRaises(LocalCacheSpecRequiredError):
        mk_cache(['https://localhost/foo', 'http://localhost/bar'])

      with self.assertRaises(RemoteCacheSpecRequiredError):
        mk_cache([tmpdir, '/bar'])

      with self.assertRaises(TooManyCacheSpecsError):
        mk_cache([tmpdir, self.REMOTE_URI_1, self.REMOTE_URI_2])

      check(S3ArtifactCache, ['s3://some-bucket/bar'])
