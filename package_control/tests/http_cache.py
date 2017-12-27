import time
import unittest

from ..http_cache import HttpCache


class HttpCacheTests(unittest.TestCase):

    def test_create_cache(self):
        key = 'test_cache_file'
        contents = b'This is a test content of the http cache test case.'

        # create and clear cache object
        cache = HttpCache(0)
        self.assertFalse(cache.has(key))

        # add an object to cache
        cache.set(key, contents)
        self.assertTrue(cache.has(key))

        # read back the cache content
        self.assertEqual(cache.get(key), contents)

        # clear cache again
        time.sleep(1)  # wait at least 1 second to ensure cache is cleard
        cache.clear(0)
        self.assertFalse(cache.has(key))
