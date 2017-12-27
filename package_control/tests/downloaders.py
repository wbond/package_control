import unittest

from .. import downloaders
from ..downloaders.exceptions import BinaryNotFoundError
from ..downloaders.exceptions import DownloaderException
from ..http_cache import HttpCache
from .consts import USER_AGENT


class DownloaderTestsMixin():

    def downloader(self):
        if not hasattr(self, '_downloader'):
            self._downloader = self.downloader_class(settings={
                'debug': True,
                'cache': HttpCache(604800),
                'cache_length': 604800,  # required to handle RateLimitException
                'user_agent': USER_AGENT
            })
        return self._downloader

    def test_download_status_200(self):

        try:
            self.assertEqual(
                self.downloader().download(
                    url=(
                        'https://raw.githubusercontent.com/packagecontrol-test'
                        '/package_control-tester/master/readme.md'
                    ),
                    error_message="",
                    timeout=20,
                    tries=3
                ),
                (
                    b'# Package Control Tester\n\nThis repo is used to test the various clients '
                    b'and providers that are part of\nPackage Control.\n'
                )
            )

        except BinaryNotFoundError:
            # CLI downloader not available
            pass

    def test_download_status_304(self):

        try:
            # This test is run after test_download_status_200(). Therefore the
            # cache, which expires 1 week after creation, should still exist and
            # therefore return exactly the same content as the previous test.
            self.assertEqual(
                self.downloader().retrieve_cached(
                    url=(
                        'https://raw.githubusercontent.com/packagecontrol-test'
                        '/package_control-tester/master/readme.md'
                    ),
                ),
                (
                    b'# Package Control Tester\n\nThis repo is used to test the various clients '
                    b'and providers that are part of\nPackage Control.\n'
                )
            )

        except BinaryNotFoundError:
            # CLI downloader not available
            pass

    def test_download_status_404(self):

        try:
            with self.assertRaises(DownloaderException):
                self.downloader().download(
                    url=(
                        'https://raw.githubusercontent.com/packagecontrol-test'
                        '/package_control-tester/master/none-existing-file.txt'
                    ),
                    error_message="",
                    timeout=20,
                    tries=1
                )

        except BinaryNotFoundError:
            # CLI downloader not available
            pass


class CurlDownloaderTests(unittest.TestCase, DownloaderTestsMixin):
    downloader_class = downloaders.CurlDownloader


class UrlLibDownloaderTests(unittest.TestCase, DownloaderTestsMixin):
    downloader_class = downloaders.UrlLibDownloader


class WgetDownloaderTests(unittest.TestCase, DownloaderTestsMixin):
    downloader_class = downloaders.WgetDownloader


if hasattr(downloaders, 'WinINetDownloader'):
    class WinINetDownloaderTests(unittest.TestCase, DownloaderTestsMixin):
        downloader_class = downloaders.WinINetDownloader
else:
    class WinINetDownloaderTests(unittest.TestCase):
        pass
