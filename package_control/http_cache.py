import os
import time

from . import sys_path


class HttpCache:

    """
    A data store for caching HTTP response data.
    """

    def __init__(self, ttl):
        """
        Constructs a new instance.

        :param ttl:
            The number of seconds a cache entry should be valid for
        """
        self.ttl = float(ttl)
        self.base_path = os.path.join(sys_path.pc_cache_dir(), 'http_cache')
        os.makedirs(self.base_path, exist_ok=True)

    def prune(self):
        """
        Removes all cache entries older than the TTL

        :param ttl:
            The number of seconds a cache entry should be valid for
        """
        try:
            for filename in os.listdir(self.base_path):
                path = os.path.join(self.base_path, filename)
                # There should not be any folders in the cache dir, but we
                # ignore to prevent an exception
                if os.path.isdir(path):
                    continue
                if os.stat(path).st_atime < time.time() - self.ttl:
                    os.unlink(path)

        except FileNotFoundError:
            pass

    def get(self, key):
        """
        Returns a cached value

        :param key:
            The key to fetch the cache for

        :return:
            The (binary) cached value, or False
        """
        try:
            cache_file = os.path.join(self.base_path, key)

            # update filetime to prevent unmodified cache files
            # from being deleted, if they are frequently accessed.
            os.utime(cache_file)

            with open(cache_file, 'rb') as fobj:
                return fobj.read()

        except FileNotFoundError:
            return False

    def has(self, key):
        cache_file = os.path.join(self.base_path, key)
        return os.path.exists(cache_file)

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

        cache_file = os.path.join(self.base_path, key)
        with open(cache_file, 'wb') as f:
            f.write(content)
