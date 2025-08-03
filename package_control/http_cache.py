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

    def age(self, key):
        """
        Return time since last modification.

        :param key:
            The key to fetch the cache for
                """
        try:
            cache_file = os.path.join(self.base_path, key)
            return time.time() - os.stat(cache_file).st_mtime
        except FileNotFoundError:
            return 2 ** 32

    def touch(self, key):
        """
        Update modification time

        :param key:
            The key to fetch the cache for
        """
        now = time.time()

        try:
            cache_file = os.path.join(self.base_path, key)
            os.utime(cache_file, (now, now))
        except FileNotFoundError:
            pass
        try:
            cache_file = os.path.join(self.base_path, key + '.info')
            os.utime(cache_file, (now, now))
        except FileNotFoundError:
            pass

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
            # NOTE: try to rely on OS updating access time (`os.stat(path).st_atime`)
            # os.utime(cache_file)

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
