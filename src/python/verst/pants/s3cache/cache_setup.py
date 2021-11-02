from __future__ import absolute_import

import os
from pants.cache.cache_setup import CacheFactory
from pants.cache.local_artifact_cache import (LocalArtifactCache,
                                              TempLocalArtifactCache)
from pants.cache.pinger import BestUrlSelector
from pants.cache.restful_artifact_cache import RESTfulArtifactCache
from six.moves import range
from verst.pants.s3cache.s3cache import S3ArtifactCache


def _is_s3(string_spec):
    return string_spec.startswith('s3://')


def is_remote(_self, string_spec):
    # both artifact cache and resolver use REST, add new protocols here once they are supported
    return (string_spec.startswith('http://') or string_spec.startswith('https://') or
            _is_s3(string_spec))


def get_available_urls(self, urls):
    return urls


def _do_create_artifact_cache(self, spec, action):
    """Returns an artifact cache for the specified spec.
    spec can be:
      - a path to a file-based cache root.
      - a URL of a RESTful cache root.
      - a URL of a S3 cache.
      - a bar-separated list of URLs, where we'll pick the one with the best ping times.
      - A list or tuple of two specs, local, then remote, each as described above
    """
    compression = self._options.compression_level
    if compression not in range(1, 10):
        raise ValueError("compression_level must be an integer 1-9: {}".format(compression))

    artifact_root = self._options.pants_workdir
    # If the artifact root is a symlink it is more efficient to readlink the symlink
    # only once in a FUSE context like VCFS. The artifact extraction root lets us extract
    # artifacts directly side-stepping a VCFS lookup if in use.
    artifact_extraction_root = (
      os.readlink(artifact_root) if os.path.islink(artifact_root) else artifact_root
    )

    def create_local_cache(parent_path):
        path = os.path.join(parent_path, self._cache_dirname)
        self._log.debug(
          "{0} {1} local artifact cache at {2}".format(self._task.stable_name(), action, path)
        )
        if self._options.max_entries_per_target is None or self._options.max_entries_per_target < 0:
          max_entries_per_target = None
        else:
          max_entries_per_target = self._options.max_entries_per_target

        return LocalArtifactCache(
          artifact_root,
          artifact_extraction_root,
          path,
          compression,
          max_entries_per_target,
          permissions=self._options.write_permissions,
          dereference=self._options.dereference_symlinks,
        )

    def create_remote_cache(remote_spec, local_cache):
        urls = self.get_available_urls(remote_spec.split("|"))

        if len(urls) > 0:
            resolved_local_cache = local_cache or TempLocalArtifactCache(
              artifact_root, artifact_extraction_root, compression
            )
            if _is_s3(urls[0]):
                self._log.debug("Using S3 cache at {}".format(urls[0]))
                return S3ArtifactCache(artifact_root, urls[0], resolved_local_cache)

            best_url_selector = BestUrlSelector(
              ["{}/{}".format(url.rstrip("/"), self._cache_dirname) for url in urls]
            )
            return RESTfulArtifactCache(
              artifact_root,
              best_url_selector,
              resolved_local_cache,
              read_timeout=self._options.read_timeout,
              write_timeout=self._options.write_timeout,
            )

    local_cache = create_local_cache(spec.local) if spec.local else None
    remote_cache = create_remote_cache(spec.remote, local_cache) if spec.remote else None
    if remote_cache:
        return remote_cache
    return local_cache


def patch():
    CacheFactory.is_remote = is_remote
    CacheFactory.get_available_urls = get_available_urls
    CacheFactory._do_create_artifact_cache = _do_create_artifact_cache
