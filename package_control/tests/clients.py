import unittest

from ..clients.readme_client import ReadmeClient
from ..clients.github_client import GitHubClient
from ..clients.bitbucket_client import BitBucketClient
from ..http_cache import HttpCache

from . import LAST_COMMIT_TIMESTAMP, LAST_COMMIT_VERSION, CLIENT_ID, CLIENT_SECRET


class GitHubClientTests(unittest.TestCase):
    maxDiff = None

    def github_settings(self):
        return {
            'debug': True,
            'cache': HttpCache(604800),
            'query_string_params': {
                'api.github.com': {
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET
                }
            }
        }

    def test_github_client_repo_info(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            {
                'name': 'package_control-tester',
                'description': 'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                'homepage': 'https://github.com/packagecontrol/package_control-tester',
                'author': 'packagecontrol',
                'readme': 'https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md',
                'issues': 'https://github.com/packagecontrol/package_control-tester/issues',
                'donate': 'https://gratipay.com/on/github/packagecontrol/'
            },
            client.repo_info('https://github.com/packagecontrol/package_control-tester')
        )

    def test_github_client_user_info(self):
        client = GitHubClient(self.github_settings())

        self.assertEqual(
            [{
                'name': 'package_control-tester',
                'description': 'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                'homepage': 'https://github.com/packagecontrol/package_control-tester',
                'author': 'packagecontrol',
                'readme': 'https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md',
                'issues': 'https://github.com/packagecontrol/package_control-tester/issues',
                'donate': 'https://gratipay.com/on/github/packagecontrol/'
            }],
            client.user_info('https://github.com/packagecontrol')
        )

    def test_github_readme(self):
        client = ReadmeClient(self.github_settings())
        self.assertEqual(
            {
                'filename': 'readme.md',
                'contents': '# Package Control Tester\n\nThis repo is used to test the various clients and providers that are part of\nPackage Control.\n',
                'format': 'markdown'
            },
            client.readme_info('https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md')
        )

    def test_github_client_branch_downloads(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            [
                {
                    'date': LAST_COMMIT_TIMESTAMP,
                    'version': LAST_COMMIT_VERSION,
                    'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/master'
                }
            ],
            client.download_info('https://github.com/packagecontrol/package_control-tester')
        )

    def test_github_client_tags_downloads(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            [
                {
                    'date': '2014-11-12 15:52:35',
                    'version': '1.0.1',
                    'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1'
                },
                {
                    'date': '2014-11-12 15:14:23',
                    'version': '1.0.1-beta',
                    'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta'
                },
                {
                    'date': '2014-11-12 15:14:13',
                    'version': '1.0.0',
                    'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0'
                },
                {
                    'date': '2014-11-12 02:02:22',
                    'version': '0.9.0',
                    'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0'
                }
            ],
            client.download_info('https://github.com/packagecontrol/package_control-tester/tags')
        )

    def test_github_client_tags_prefix_downloads(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            [
                {
                    'date': '2014-11-28 20:54:15',
                    'version': '1.0.2',
                    'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/win-1.0.2'
                }
            ],
            client.download_info('https://github.com/packagecontrol/package_control-tester/tags', 'win-')
        )


class BitBucketClientTests(unittest.TestCase):
    maxDiff = None

    def bitbucket_settings(self):
        return {
            'debug': True,
            'cache': HttpCache(604800)
        }

    def test_bitbucket_client_repo_info(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            {
                'name': 'package_control-tester',
                'description': 'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                'homepage': 'https://bitbucket.org/wbond/package_control-tester',
                'author': 'wbond',
                'readme': 'https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md',
                'issues': 'https://bitbucket.org/wbond/package_control-tester/issues',
                'donate': 'https://gratipay.com/on/bitbucket/wbond/'
            },
            client.repo_info('https://bitbucket.org/wbond/package_control-tester')
        )

    def test_bitbucket_readme(self):
        client = ReadmeClient(self.bitbucket_settings())
        self.assertEqual(
            {
                'filename': 'readme.md',
                'contents': '# Package Control Tester\n\nThis repo is used to test the various clients and providers that are part of\nPackage Control.\n',
                'format': 'markdown'
            },
            client.readme_info('https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md')
        )

    def test_bitbucket_client_branch_downloads(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            [
                {
                    'date': LAST_COMMIT_TIMESTAMP,
                    'version': LAST_COMMIT_VERSION,
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/master.zip'
                }
            ],
            client.download_info('https://bitbucket.org/wbond/package_control-tester')
        )

    def test_bitbucket_client_tags_downloads(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            [
                {
                    'date': '2014-11-12 15:52:35',
                    'version': '1.0.1',
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip'
                },
                {
                    'date': '2014-11-12 15:14:23',
                    'version': '1.0.1-beta',
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip'
                },
                {
                    'date': '2014-11-12 15:14:13',
                    'version': '1.0.0',
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip'
                },
                {
                    'date': '2014-11-12 02:02:22',
                    'version': '0.9.0',
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip'
                }
            ],
            client.download_info('https://bitbucket.org/wbond/package_control-tester#tags')
        )

    def test_bitbucket_client_tags_prefix_downloads(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            [
                {
                    'date': '2014-11-28 20:54:15',
                    'version': '1.0.2',
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/win-1.0.2.zip'
                }
            ],
            client.download_info('https://bitbucket.org/wbond/package_control-tester#tags', 'win-')
        )
