import logging
import os
from functools import wraps

import boto
from boto.exception import StorageResponseError, BotoClientError, BotoServerError
from pants.cache.artifact_cache import (ArtifactCache,
                                        NonfatalArtifactCacheError,
                                        UnreadableArtifact)
from pyjavaproperties import Properties
from six.moves.urllib.parse import urlparse

logger = logging.getLogger(__name__)
CONFIG_FILE = os.path.expanduser('~/.pants/.s3credentials')


def trap_s3_errors(func):
  @wraps(func)
  def error_decorator(self, cache_key, *args, **kwargs):
    try:
      return func(self, cache_key, *args, **kwargs)
    except NonfatalArtifactCacheError as e:
      raise e
    except BotoClientError as e:
      logger.warn('\nError while calling remote artifact cache: {0}\n'.format(e))
      raise NonfatalArtifactCacheError(cache_key, str(e))
    except BotoServerError as e:
      logger.warn('\nError while calling remote artifact cache: {0}\n'.format(e))
      raise NonfatalArtifactCacheError(cache_key, str(e))

  return error_decorator


def connect_to_s3():
  boto_kwargs = {}
  try:
    with open(CONFIG_FILE, 'r') as f:
      p = Properties()
      p.load(f)

      access_key = p.get('accessKey')
      if access_key:
        logger.debug('Reading access key from {0}'.format(CONFIG_FILE))
        boto_kwargs['aws_access_key_id'] = access_key

      secret_key = p.get('secretKey')
      if secret_key:
        logger.debug('Reading access key from {0}'.format(CONFIG_FILE))
        boto_kwargs['aws_secret_access_key'] = secret_key
  except IOError:
    logger.debug('Could not load {0}, using ENV vars'.format(CONFIG_FILE))

  s3 = boto.connect_s3(**boto_kwargs)
  s3.http_connection_kwargs['timeout'] = 4.0
  return s3

s3 = connect_to_s3()


class S3ArtifactCache(ArtifactCache):
  """An artifact cache that stores the artifacts on S3."""

  def __init__(self, artifact_root, s3_url, local):
    """
    :param artifact_root: The path under which cacheable products will be read/written
    :param s3_url: URL of the form s3://bucket/path/to/store/artifacts
    :param BaseLocalArtifactCache local: local cache instance for storing and creating artifacts
    """
    super(S3ArtifactCache, self).__init__(artifact_root)
    url = urlparse(s3_url)

    self._path = url.path
    if self._path.startswith('/'):
      self._path = self._path[1:]
    self._localcache = local
    self._bucket = s3.get_bucket(url.netloc, validate=False)

  @trap_s3_errors
  def try_insert(self, cache_key, paths):
    logger.debug('Insert {0}'.format(cache_key))
    # Delegate creation of artifacts to the local cache
    with self._localcache.insert_paths(cache_key, paths) as tarfile:
      # Upload local artifact to remote cache
      with open(tarfile, 'rb') as infile:
        s3_object = self._get_object(cache_key)
        try:
          s3_object.set_contents_from_file(infile)
        except StorageResponseError as e:
          raise NonfatalArtifactCacheError('Failed to PUT {0}: {1}'.format(cache_key, str(e)))

  @trap_s3_errors
  def has(self, cache_key):
    logger.debug('Has {0}'.format(cache_key))
    if self._localcache.has(cache_key):
      return True
    return self._get_object(cache_key).exists()

  @trap_s3_errors
  def use_cached_files(self, cache_key, results_dir=None):
    logger.debug('Get {0}'.format(cache_key))
    if self._localcache.has(cache_key):
      return self._localcache.use_cached_files(cache_key, results_dir)

    s3_object = self._get_object(cache_key)
    try:
      s3_object.open_read()

      # Delegate storage and extraction to local cache
      return self._localcache.store_and_use_artifact(cache_key, s3_object, results_dir)
    except StorageResponseError as e:
      logger.info('\nStorage error (possible cache miss) while reading: {0}\n'.format(e))
      return False
    except Exception as e:
      logger.warn('\nError while reading form remote artifact cache: {0}\n'.format(e))
      return UnreadableArtifact(cache_key, e)
    finally:
      s3_object.close()

  @trap_s3_errors
  def delete(self, cache_key):
    logger.debug("Delete {0}".format(cache_key))
    self._localcache.delete(cache_key)
    self._get_object(cache_key).delete()

  @trap_s3_errors
  def _get_object(self, cache_key):
    return self._bucket.get_key(self._path_for_key(cache_key), validate=False)

  def _path_for_key(self, cache_key):
    return '{0}/{1}/{2}.tgz'.format(self._path, cache_key.id, cache_key.hash)
