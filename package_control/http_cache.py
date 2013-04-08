import os
import time

import sublime

from .open_compat import open_compat, read_compat


class HttpCache(object):
    """
    A data store for caching HTTP response data.
    """

    def __init__(self, ttl):
        self.base_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.cache')
        if not os.path.exists(self.base_path):
            os.mkdir(self.base_path)
        self.clear(int(ttl))

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

        cache_file = os.path.join(self.base_path, key)
        if not os.path.exists(cache_file):
            return False

        with open_compat(cache_file, 'rb') as f:
            return read_compat(f)

    def has(self, key):
        cache_file = os.path.join(self.base_path, key)
        return os.path.exists(cache_file)

    def set(self, key, content):
        """
        Saves a value in the cache

        :param key:
            The key to save the cache with

        :param content:
            The (binary) content to cache
        """

        cache_file = os.path.join(self.base_path, key)
        with open_compat(cache_file, 'wb') as f:
            f.write(content)
