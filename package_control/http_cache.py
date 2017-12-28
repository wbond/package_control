import os
import time

from .path import cache_path


class HttpCache(object):

    """
    A data store for caching HTTP response data.
    """

    def __init__(self, ttl):
        """
        Initialize the HttpCache object.

        Ensure the http cache folder exists and out-dated entries are removed.
        """
        self.base_path = os.path.join(cache_path(), 'http')
        os.makedirs(self.base_path, mode=0o555, exist_ok=True)

        self.clear(ttl)

    def clear(self, ttl):
        """
        Removes all cache entries older than the TTL

        :param ttl:
            The number of seconds a cache entry should be valid for
        """

        ttl = int(ttl)

        for filename in os.listdir(self.base_path):
            path = os.path.join(self.base_path, filename)
            # There should not be any folders in the cache dir, but we
            # ignore to prevent an exception
            if os.path.isdir(path):
                continue
            mtime = os.stat(path).st_mtime
            if mtime < time.time() - ttl:
                os.unlink(path)

    def get(self, key):
        """
        Returns a cached value

        :param key:
            The key to fetch the cache for

        :return:
            The (binary) cached value, or False
        """
        try:
            with open(self.path(key), 'rb') as f:
                return f.read()
        except FileNotFoundError:
            return False

    def has(self, key):
        return os.path.exists(self.path(key))

    def path(self, key):
        """
        Returns the filesystem path to the key

        :param key:
            The key to get the path for

        :return:
            The absolute filesystem path to the cache file
        """

        return os.path.join(self.base_path, key)

    def set(self, key, content):
        """
        Saves a value in the cache

        :param key:
            The key to save the cache with

        :param content:
            The (binary) content to cache
        """

        with open(self.path(key), 'wb') as f:
            f.write(content)
