import unittest

from ..clients.readme_client import ReadmeClient
from ..clients.github_client import GitHubClient
from ..clients.gitlab_client import GitLabClient
from ..clients.bitbucket_client import BitBucketClient
from ..http_cache import HttpCache

from ._config import (
    BB_PASS,
    BB_USER,
    DEBUG,
    GH_PASS,
    GH_USER,
    GL_PASS,
    GL_USER,
    LAST_COMMIT_TIMESTAMP,
    LAST_COMMIT_VERSION,
    USER_AGENT,
)


class GitHubClientTests(unittest.TestCase):
    maxDiff = None

    def github_settings(self):
        if not GH_PASS:
            self.skipTest("GitHub personal access token for %s not set via env var GH_PASS" % GH_USER)

        return {
            'debug': DEBUG,
            'cache': HttpCache(604800),
            'cache_length': 604800,
            'user_agent': USER_AGENT,
            'http_basic_auth': {
                'api.github.com': [GH_USER, GH_PASS],
                'raw.githubusercontent.com': [GH_USER, GH_PASS],
            }
        }

    def test_github_client_repo_user_branch_00(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://github.com')
        )
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://github.com/')
        )

    def test_github_client_repo_user_branch_01(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            ('packagecontrol-test', None, None),
            client.user_repo_branch('https://github.com/packagecontrol-test')
        )
        self.assertEqual(
            ('packagecontrol-test', None, None),
            client.user_repo_branch('https://github.com/packagecontrol-test/')
        )

    def test_github_client_repo_user_branch_02(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester/')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester.git')
        )

    def test_github_client_repo_user_branch_03(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', 'master'),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester/tree/master')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', 'master'),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester/tree/master/')
        )

    def test_github_client_repo_user_branch_04(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester/tags')
        )
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://github.com/packagecontrol-test/package_control-tester/tags/')
        )

    def test_github_client_repo_user_branch_05(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://github;com/packagecontrol-test/package_control-tester')
        )

    def test_github_client_repo_info(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            {
                'name': 'package_control-tester',
                'description': 'A test of Package Control upgrade messages with '
                               'explicit versions, but date-based releases.',
                'homepage': 'https://github.com/packagecontrol-test/package_control-tester',
                'author': 'packagecontrol-test',
                'readme': 'https://raw.githubusercontent.com/packagecontrol-test'
                          '/package_control-tester/master/readme.md',
                'issues': 'https://github.com/packagecontrol-test/package_control-tester/issues',
                'donate': None,
                'default_branch': 'master'
            },
            client.repo_info('https://github.com/packagecontrol-test/package_control-tester')
        )

    def test_github_client_user_info(self):
        client = GitHubClient(self.github_settings())

        self.assertEqual(
            [{
                'name': 'package_control-tester',
                'description': 'A test of Package Control upgrade messages with '
                               'explicit versions, but date-based releases.',
                'homepage': 'https://github.com/packagecontrol-test/package_control-tester',
                'author': 'packagecontrol-test',
                'readme': 'https://raw.githubusercontent.com/packagecontrol-test'
                          '/package_control-tester/master/readme.md',
                'issues': 'https://github.com/packagecontrol-test/package_control-tester/issues',
                'donate': None,
                'default_branch': 'master'
            }],
            client.user_info('https://github.com/packagecontrol-test')
        )

    def test_github_readme(self):
        client = ReadmeClient(self.github_settings())
        self.assertEqual(
            {
                'filename': 'readme.md',
                'contents': '# Package Control Tester\n\nThis repo is used to test the '
                            'various clients and providers that are part of\nPackage Control.\n',
                'format': 'markdown'
            },
            client.readme_info(
                'https://raw.githubusercontent.com/packagecontrol-test/package_control-tester/master/readme.md'
            )
        )

    def test_github_client_branch_downloads(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            [
                {
                    'date': LAST_COMMIT_TIMESTAMP,
                    'version': LAST_COMMIT_VERSION,
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/master'
                }
            ],
            client.download_info('https://github.com/packagecontrol-test/package_control-tester')
        )

    def test_github_client_tags_downloads(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            [
                {
                    'date': '2014-11-12 15:52:35',
                    'version': '1.0.1',
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/1.0.1'
                },
                {
                    'date': '2014-11-12 15:14:23',
                    'version': '1.0.1-beta',
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/1.0.1-beta'
                },
                {
                    'date': '2014-11-12 15:14:13',
                    'version': '1.0.0',
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/1.0.0'
                },
                {
                    'date': '2014-11-12 02:02:22',
                    'version': '0.9.0',
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/0.9.0'
                }
            ],
            client.download_info('https://github.com/packagecontrol-test/package_control-tester/tags')
        )

    def test_github_client_limited_tags_downloads(self):
        settings = self.github_settings()
        settings['max_releases'] = 1
        client = GitHubClient(settings)
        self.assertEqual(
            [
                {
                    'date': '2014-11-12 15:52:35',
                    'version': '1.0.1',
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/1.0.1'
                }
            ],
            client.download_info('https://github.com/packagecontrol-test/package_control-tester/tags')
        )

    def test_github_client_tags_prefix_downloads(self):
        client = GitHubClient(self.github_settings())
        self.assertEqual(
            [
                {
                    'date': '2014-11-28 20:54:15',
                    'version': '1.0.2',
                    'url': 'https://codeload.github.com/packagecontrol-test/package_control-tester/zip/win-1.0.2'
                }
            ],
            client.download_info('https://github.com/packagecontrol-test/package_control-tester/tags', 'win-')
        )


class GitLabClientTests(unittest.TestCase):
    maxDiff = None

    def gitlab_settings(self):
        if not GL_PASS:
            self.skipTest("GitLab personal access token for %s not set via env var GL_PASS" % GL_USER)

        return {
            'debug': DEBUG,
            'cache': HttpCache(604800),
            'cache_length': 604800,
            'user_agent': USER_AGENT,
            'http_basic_auth': {
                'gitlab.com': [GL_USER, GL_PASS]
            }
        }

    def test_gitlab_client_repo_user_branch_00(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://gitlab.com')
        )
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://gitlab.com/')
        )

    def test_gitlab_client_repo_user_branch_01(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            ('packagecontrol-test', None, None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test')
        )
        self.assertEqual(
            ('packagecontrol-test', None, None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/')
        )

    def test_gitlab_client_repo_user_branch_02(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester/')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester.git')
        )

    def test_gitlab_client_repo_user_branch_03(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', 'master'),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', 'master'),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master/')
        )

    def test_gitlab_client_repo_user_branch_04(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester/-/tags')
        )
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://gitlab.com/packagecontrol-test/package_control-tester/-/tags/')
        )

    def test_gitlab_client_repo_user_branch_05(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://gitlab;com/packagecontrol-test/package_control-tester')
        )

    def test_gitlab_client_repo_info(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            {
                'name': 'package_control-tester',
                'description':
                    'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                'readme':
                    'https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md',
                'author': 'packagecontrol-test',
                'issues': None,
                'donate': None,
                'default_branch': 'master'
            },
            client.repo_info(
                'https://gitlab.com/packagecontrol-test/package_control-tester'
            )
        )

    def test_gitlab_client_user_info(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            [
                {
                    'name': 'package_control-tester',
                    'description':
                        'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                    'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                    'readme': 'https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md',
                    'author': 'packagecontrol-test',
                    'issues': None,
                    'donate': None,
                    'default_branch': 'master'
                }
            ],
            client.user_info(
                'https://gitlab.com/packagecontrol-test'
            )
        )

    def test_gitlab_readme(self):
        client = ReadmeClient(self.gitlab_settings())
        self.assertEqual(
            {
                'filename': 'readme.md',
                'contents':
                    '# Package Control Tester\n\nThis repo is used to test the '
                    'various clients and providers that are part of\nPackage Control.\n',
                'format': 'markdown'
            },
            client.readme_info(
                'https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md'
            )
        )

    def test_gitlab_client_branch_downloads(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            [
                {
                    'date': '2020-07-15 10:50:38',
                    'version': '2020.07.15.10.50.38',
                    'url':
                        'https://gitlab.com/packagecontrol-test/package_control-tester'
                        '/-/archive/master/package_control-tester-master.zip'
                }
            ],
            client.download_info(
                'https://gitlab.com/packagecontrol-test/package_control-tester'
            )
        )

    def test_gitlab_client_tags_downloads(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            [
                {
                    'date': '2020-07-15 10:50:38',
                    'version': '1.0.1',
                    'url':
                        'https://gitlab.com/packagecontrol-test/package_control-tester'
                        '/-/archive/1.0.1/package_control-tester-1.0.1.zip'
                }
            ],
            client.download_info(
                'https://gitlab.com/packagecontrol-test/package_control-tester/-/tags'
            )
        )

    def test_gitlab_client_tags_prefix_downloads(self):
        client = GitLabClient(self.gitlab_settings())
        self.assertEqual(
            [
                {
                    'date': '2020-07-15 10:50:38',
                    'version': '1.0.1',
                    'url':
                        'https://gitlab.com/packagecontrol-test/package_control-tester/'
                        '-/archive/win-1.0.1/package_control-tester-win-1.0.1.zip'
                }
            ],
            client.download_info(
                'https://gitlab.com/packagecontrol-test/package_control-tester/-/tags',
                'win-'
            )
        )


class BitBucketClientTests(unittest.TestCase):
    maxDiff = None

    def bitbucket_settings(self):
        if not BB_PASS:
            self.skipTest("BitBucket app password for %s not set via env var BB_PASS" % BB_USER)

        return {
            'debug': DEBUG,
            'cache': HttpCache(604800),
            'cache_length': 604800,
            'user_agent': USER_AGENT,
            'http_basic_auth': {
                'api.bitbucket.org': [BB_USER, BB_PASS]
            }
        }

    def test_bitbucket_client_repo_user_branch_00(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://bitbucket.org')
        )
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://bitbucket.org/')
        )

    def test_bitbucket_client_repo_user_branch_01(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            ('packagecontrol-test', None, None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test')
        )
        self.assertEqual(
            ('packagecontrol-test', None, None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/')
        )

    def test_bitbucket_client_repo_user_branch_02(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester/')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester.git')
        )

    def test_bitbucket_client_repo_user_branch_03(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', 'master'),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester/src/master')
        )
        self.assertEqual(
            ('packagecontrol-test', 'package_control-tester', 'master'),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester/src/master/')
        )

    def test_bitbucket_client_repo_user_branch_04(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester#tags')
        )
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://bitbucket.org/packagecontrol-test/package_control-tester/#tags')
        )

    def test_bitbucket_client_repo_user_branch_05(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            (None, None, None),
            client.user_repo_branch('https://bitbucket;com/packagecontrol-test/package_control-tester')
        )

    def test_bitbucket_client_repo_info(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(
            {
                'name': 'package_control-tester',
                'description': 'A test of Package Control upgrade messages with '
                               'explicit versions, but date-based releases.',
                'homepage': 'https://bitbucket.org/wbond/package_control-tester',
                'author': 'wbond',
                'readme': 'https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md',
                'issues': 'https://bitbucket.org/wbond/package_control-tester/issues',
                'donate': None,
                'default_branch': 'master'
            },
            client.repo_info('https://bitbucket.org/wbond/package_control-tester')
        )

    def test_bitbucket_client_user_info(self):
        client = BitBucketClient(self.bitbucket_settings())
        self.assertEqual(None, client.user_info('https://bitbucket.org/wbond'))

    def test_bitbucket_readme(self):
        client = ReadmeClient(self.bitbucket_settings())
        self.assertEqual(
            {
                'filename': 'readme.md',
                'contents': '# Package Control Tester\n\nThis repo is used to test the various '
                            'clients and providers that are part of\nPackage Control.\n',
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

    def test_bitbucket_client_limited_tags_downloads(self):
        settings = self.bitbucket_settings()
        settings['max_releases'] = 1
        client = BitBucketClient(settings)
        self.assertEqual(
            [
                {
                    'date': '2014-11-12 15:52:35',
                    'version': '1.0.1',
                    'url': 'https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip'
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
