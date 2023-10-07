import unittest

from ..http_cache import HttpCache
from ..providers.bitbucket_repository_provider import BitBucketRepositoryProvider
from ..providers.channel_provider import ChannelProvider, InvalidChannelFileException
from ..providers.github_repository_provider import GitHubRepositoryProvider
from ..providers.github_user_provider import GitHubUserProvider
from ..providers.gitlab_repository_provider import GitLabRepositoryProvider
from ..providers.gitlab_user_provider import GitLabUserProvider
from ..providers.json_repository_provider import JsonRepositoryProvider

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


class GitHubRepositoryProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(
            True,
            GitHubRepositoryProvider.match_url('https://github.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            True,
            GitHubRepositoryProvider.match_url('https://github.com/packagecontrol-test/package_control-tester/')
        )
        self.assertEqual(
            True,
            GitHubRepositoryProvider.match_url(
                'https://github.com/packagecontrol-test/package_control-tester/tree/master'
            )
        )
        self.assertEqual(
            False,
            GitHubRepositoryProvider.match_url('https://github.com/packagecontrol-test')
        )
        self.assertEqual(
            False,
            GitHubRepositoryProvider.match_url('https://github,com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            False,
            GitHubRepositoryProvider.match_url('https://gitlab.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            False,
            GitHubRepositoryProvider.match_url('https://bitbucket.org/wbond/package_control-tester')
        )

    def test_get_packages(self):
        provider = GitHubRepositoryProvider(
            'https://github.com/packagecontrol-test/package_control-tester',
            self.github_settings()
        )
        self.assertEqual(
            [(
                'package_control-tester',
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
                    'buy': None,
                    'sources': ['https://github.com/packagecontrol-test/package_control-tester'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [
                        {
                            'date': LAST_COMMIT_TIMESTAMP,
                            'version': LAST_COMMIT_VERSION,
                            'url': 'https://codeload.github.com/packagecontrol-test'
                                   '/package_control-tester/zip/master',
                            'sublime_text': '*',
                            'platforms': ['*']
                        }
                    ],
                    'last_modified': LAST_COMMIT_TIMESTAMP
                }
            )],
            list(provider.get_packages())
        )

    def test_get_sources(self):
        provider = GitHubRepositoryProvider(
            'https://github.com/packagecontrol-test/package_control-tester',
            self.github_settings()
        )
        self.assertEqual(
            ['https://github.com/packagecontrol-test/package_control-tester'],
            provider.get_sources()
        )

    def test_get_renamed_packages(self):
        provider = GitHubRepositoryProvider(
            'https://github.com/packagecontrol-test/package_control-tester',
            self.github_settings()
        )
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = GitHubRepositoryProvider(
            'https://github.com/packagecontrol-test/package_control-tester',
            self.github_settings()
        )
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_libraries(self):
        provider = GitHubRepositoryProvider(
            'https://github.com/packagecontrol-test/package_control-tester',
            self.github_settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitHubRepositoryProvider(
            'https://github.com/packagecontrol-test/package_control-tester',
            self.github_settings()
        )
        self.assertEqual([], list(provider.get_broken_libraries()))


class GitHubUserProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(
            True,
            GitHubUserProvider.match_url('https://github.com/packagecontrol-test')
        )
        self.assertEqual(
            True,
            GitHubUserProvider.match_url('https://github.com/packagecontrol-test/')
        )
        self.assertEqual(
            False,
            GitHubUserProvider.match_url('https://github,com/packagecontrol-test')
        )
        self.assertEqual(
            False,
            GitHubUserProvider.match_url('https://github.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            False,
            GitHubUserProvider.match_url('https://github.com/packagecontrol-test/package_control-tester/tree/master')
        )
        self.assertEqual(
            False,
            GitHubUserProvider.match_url('https://bitbucket.org/packagecontrol-test')
        )

    def test_get_packages(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol-test', self.github_settings())
        self.assertEqual(
            [(
                'package_control-tester',
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
                    'buy': None,
                    'sources': ['https://github.com/packagecontrol-test'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [
                        {
                            'date': LAST_COMMIT_TIMESTAMP,
                            'version': LAST_COMMIT_VERSION,
                            'url': 'https://codeload.github.com/packagecontrol-test'
                                   '/package_control-tester/zip/master',
                            'sublime_text': '*',
                            'platforms': ['*']
                        }
                    ],
                    'last_modified': LAST_COMMIT_TIMESTAMP
                }
            )],
            list(provider.get_packages())
        )

    def test_get_sources(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol-test', self.github_settings())
        self.assertEqual(['https://github.com/packagecontrol-test'], provider.get_sources())

    def test_get_renamed_packages(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol-test', self.github_settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol-test', self.github_settings())
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_libraries(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol-test', self.github_settings())
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol-test', self.github_settings())
        self.assertEqual([], list(provider.get_broken_libraries()))


class GitLabRepositoryProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(
            True,
            GitLabRepositoryProvider.match_url('https://gitlab.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            True,
            GitLabRepositoryProvider.match_url('https://gitlab.com/packagecontrol-test/package_control-tester/')
        )
        self.assertEqual(
            True,
            GitLabRepositoryProvider.match_url(
                'https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master'
            )
        )
        self.assertEqual(
            False,
            GitLabRepositoryProvider.match_url('https://gitlab.com/packagecontrol-test')
        )
        self.assertEqual(
            False,
            GitLabRepositoryProvider.match_url('https://gitlab,com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            False,
            GitLabRepositoryProvider.match_url('https://github.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            False,
            GitLabRepositoryProvider.match_url('https://bitbucket.org/wbond/package_control-tester')
        )

    def test_get_packages(self):
        provider = GitLabRepositoryProvider(
            'https://gitlab.com/packagecontrol-test/package_control-tester',
            self.gitlab_settings()
        )
        self.assertEqual(
            [(
                'package_control-tester',
                {
                    'name': 'package_control-tester',
                    'description': 'A test of Package Control upgrade messages with '
                                   'explicit versions, but date-based releases.',
                    'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                    'author': 'packagecontrol-test',
                    'readme': 'https://gitlab.com/packagecontrol-test/'
                              'package_control-tester/-/raw/master/readme.md',
                    'issues': None,
                    'donate': None,
                    'buy': None,
                    'sources': ['https://gitlab.com/packagecontrol-test/package_control-tester'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [
                        {
                            'date': '2020-07-15 10:50:38',
                            'version': '2020.07.15.10.50.38',
                            'url': 'https://gitlab.com/packagecontrol-test/'
                                   'package_control-tester/-/archive/master/'
                                   'package_control-tester-master.zip',
                            'sublime_text': '*',
                            'platforms': ['*']
                        }
                    ],
                    'last_modified': '2020-07-15 10:50:38'
                }
            )],
            list(provider.get_packages())
        )

    def test_get_sources(self):
        provider = GitLabRepositoryProvider(
            'https://gitlab.com/packagecontrol-test/package_control-tester',
            self.gitlab_settings()
        )
        self.assertEqual(
            ['https://gitlab.com/packagecontrol-test/package_control-tester'],
            provider.get_sources()
        )

    def test_get_renamed_packages(self):
        provider = GitLabRepositoryProvider(
            'https://gitlab.com/packagecontrol-test/package_control-tester',
            self.gitlab_settings()
        )
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = GitLabRepositoryProvider(
            'https://gitlab.com/packagecontrol-test/package_control-tester',
            self.gitlab_settings()
        )
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_libraries(self):
        provider = GitLabRepositoryProvider(
            'https://gitlab.com/packagecontrol-test/package_control-tester',
            self.gitlab_settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitLabRepositoryProvider(
            'https://gitlab.com/packagecontrol-test/package_control-tester',
            self.gitlab_settings()
        )
        self.assertEqual([], list(provider.get_broken_libraries()))


class GitLabUserProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(
            True,
            GitLabUserProvider.match_url('https://gitlab.com/packagecontrol-test')
        )
        self.assertEqual(
            True,
            GitLabUserProvider.match_url('https://gitlab.com/packagecontrol-test/')
        )
        self.assertEqual(
            False,
            GitLabUserProvider.match_url('https://gitlab,com/packagecontrol-test')
        )
        self.assertEqual(
            False,
            GitLabUserProvider.match_url('https://gitlab.com/packagecontrol-test/package_control-tester')
        )
        self.assertEqual(
            False,
            GitLabUserProvider.match_url('https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master')
        )
        self.assertEqual(
            False,
            GitLabUserProvider.match_url('https://bitbucket.org/packagecontrol-test')
        )

    def test_get_packages(self):
        provider = GitLabUserProvider('https://gitlab.com/packagecontrol-test', self.gitlab_settings())
        self.assertEqual(
            [(
                'package_control-tester',
                {
                    'name': 'package_control-tester',
                    'description': 'A test of Package Control upgrade messages with '
                                   'explicit versions, but date-based releases.',
                    'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                    'author': 'packagecontrol-test',
                    'readme': 'https://gitlab.com/packagecontrol-test/'
                              'package_control-tester/-/raw/master/readme.md',
                    'issues': None,
                    'donate': None,
                    'buy': None,
                    'sources': ['https://gitlab.com/packagecontrol-test'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [{
                        'sublime_text': '*',
                        'date': '2020-07-15 10:50:38',
                        'version': '2020.07.15.10.50.38',
                        'platforms': ['*'],
                        'url': 'https://gitlab.com/packagecontrol-test/'
                        'package_control-tester/-/archive/master/package_control-tester-master.zip'
                    }],
                    'last_modified': '2020-07-15 10:50:38'
                }
            )],
            list(provider.get_packages())
        )

    def test_get_sources(self):
        provider = GitLabUserProvider('https://gitlab.com/packagecontrol-test', self.gitlab_settings())
        self.assertEqual(['https://gitlab.com/packagecontrol-test'], provider.get_sources())

    def test_get_renamed_packages(self):
        provider = GitLabUserProvider('https://gitlab.com/packagecontrol-test', self.gitlab_settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = GitLabUserProvider('https://gitlab.com/packagecontrol-test', self.gitlab_settings())
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_libraries(self):
        provider = GitLabUserProvider('https://gitlab.com/packagecontrol-test', self.gitlab_settings())
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitLabUserProvider('https://gitlab.com/packagecontrol-test', self.gitlab_settings())
        self.assertEqual([], list(provider.get_broken_libraries()))


class BitBucketRepositoryProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(
            True,
            BitBucketRepositoryProvider.match_url('https://bitbucket.org/wbond/package_control-tester')
        )
        self.assertEqual(
            True,
            BitBucketRepositoryProvider.match_url('https://bitbucket.org/wbond/package_control-tester/')
        )
        self.assertEqual(
            True,
            BitBucketRepositoryProvider.match_url(
                'https://bitbucket.org/wbond/package_control-tester/src/master'
            )
        )
        self.assertEqual(
            False,
            BitBucketRepositoryProvider.match_url('https://bitbucket.org/wbond')
        )
        self.assertEqual(
            False,
            BitBucketRepositoryProvider.match_url('https://bitbucket,org/wbond/package_control-tester')
        )
        self.assertEqual(
            False,
            BitBucketRepositoryProvider.match_url('https://github.com/wbond/package_control-tester')
        )
        self.assertEqual(
            False,
            BitBucketRepositoryProvider.match_url('https://gitlab.com/wbond/package_control-tester')
        )

    def test_get_packages(self):
        provider = BitBucketRepositoryProvider(
            'https://bitbucket.org/wbond/package_control-tester',
            self.bitbucket_settings()
        )
        self.assertEqual(
            [(
                'package_control-tester',
                {
                    'name': 'package_control-tester',
                    'description': 'A test of Package Control upgrade messages with '
                                   'explicit versions, but date-based releases.',
                    'homepage': 'https://bitbucket.org/wbond/package_control-tester',
                    'author': 'wbond',
                    'readme': 'https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md',
                    'issues': 'https://bitbucket.org/wbond/package_control-tester/issues',
                    'donate': None,
                    'buy': None,
                    'sources': ['https://bitbucket.org/wbond/package_control-tester'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [
                        {
                            'date': LAST_COMMIT_TIMESTAMP,
                            'version': LAST_COMMIT_VERSION,
                            'url': 'https://bitbucket.org/wbond/package_control-tester/get/master.zip',
                            'sublime_text': '*',
                            'platforms': ['*']
                        }
                    ],
                    'last_modified': LAST_COMMIT_TIMESTAMP
                }
            )],
            list(provider.get_packages())
        )

    def test_get_sources(self):
        provider = BitBucketRepositoryProvider(
            'https://bitbucket.org/wbond/package_control-tester',
            self.bitbucket_settings()
        )
        self.assertEqual(
            ['https://bitbucket.org/wbond/package_control-tester'],
            provider.get_sources()
        )

    def test_get_renamed_packages(self):
        provider = BitBucketRepositoryProvider(
            'https://bitbucket.org/wbond/package_control-tester',
            self.bitbucket_settings()
        )
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = BitBucketRepositoryProvider(
            'https://bitbucket.org/wbond/package_control-tester',
            self.bitbucket_settings()
        )
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_libraries(self):
        provider = BitBucketRepositoryProvider(
            'https://bitbucket.org/wbond/package_control-tester',
            self.bitbucket_settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = BitBucketRepositoryProvider(
            'https://bitbucket.org/wbond/package_control-tester',
            self.bitbucket_settings()
        )
        self.assertEqual([], list(provider.get_broken_libraries()))


class JsonRepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        if not GH_PASS:
            self.skipTest("GitHub personal access token for %s not set via env var GH_PASS" % GH_USER)
        if not GL_PASS:
            self.skipTest("GitLab personal access token for %s not set via env var GL_PASS" % GL_USER)
        if not BB_PASS:
            self.skipTest("BitBucket app password for %s not set via env var BB_PASS" % BB_USER)

        return {
            'debug': DEBUG,
            'cache': HttpCache(604800),
            'cache_length': 604800,
            'user_agent': USER_AGENT,
            'http_basic_auth': {
                'api.github.com': [GH_USER, GH_PASS],
                'raw.githubusercontent.com': [GH_USER, GH_PASS],
                'gitlab.com': [GL_USER, GL_PASS],
                'api.bitbucket.org': [BB_USER, BB_PASS],
            }
        }

    def test_get_packages_10(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json',
            self.settings()
        )
        self.assertEqual([], list(provider.get_packages()))

    def test_get_libraries_10(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json',
            self.settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_packages_12(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json',
            self.settings()
        )
        self.assertEqual([], list(provider.get_packages()))

    def test_get_libraries_12(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json',
            self.settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_packages_20_explicit(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json',
            self.settings()
        )
        self.assertEqual(
            [(
                'package_control-tester-2.0',
                {
                    "name": "package_control-tester-2.0",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                    "issues": None,
                    "donate": None,
                    "buy": "https://example.com",
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": [
                        'https://raw.githubusercontent.com/wbond/package_control-json'
                        '/master/repository-2.0-explicit.json'
                    ],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            list(provider.get_packages())
        )

    def test_get_libraries_20(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json',
            self.settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_packages_20_github(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-github_details.json',
            self.settings()
        )
        self.assertEqual(
            [(
                'package_control-tester-2.0-gh',
                {
                    "name": "package_control-tester-2.0-gh",
                    "author": "packagecontrol-test",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                    "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                    "donate": None,
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                              "/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": [
                        'https://raw.githubusercontent.com/wbond/package_control-json'
                        '/master/repository-2.0-github_details.json',
                        "https://github.com/packagecontrol-test/package_control-tester"
                    ],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            list(provider.get_packages())
        )

    def test_get_packages_20_bitbucket(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json'
            '/master/repository-2.0-bitbucket_details.json',
            self.settings()
        )
        self.assertEqual(
            [(
                'package_control-tester-2.0-bb',
                {
                    "name": "package_control-tester-2.0-bb",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": None,
                    "buy": None,
                    "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": [
                        'https://raw.githubusercontent.com/wbond/package_control-json'
                        '/master/repository-2.0-bitbucket_details.json',
                        "https://bitbucket.org/wbond/package_control-tester"
                    ],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            list(provider.get_packages())
        )

    def test_get_packages_300_explicit(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json',
            self.settings()
        )
        self.assertEqual(
            [(
                'package_control-tester-3.0.0',
                {
                    "name": "package_control-tester-3.0.0",
                    "author": ["packagecontrol", "wbond"],
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                    "issues": None,
                    "donate": "https://gratipay.com/wbond/",
                    "buy": "https://example.com",
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": [
                        'https://raw.githubusercontent.com/wbond/package_control-json'
                        '/master/repository-3.0.0-explicit.json'
                    ],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"],
                            "libraries": ["bz2"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            list(provider.get_packages())
        )

    def test_get_libraries_300_explicit(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    'bz2',
                    {
                        "name": "bz2",
                        "author": "wbond",
                        "description": "Python bz2 module",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-explicit.json'
                        ],
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "https://packagecontrol.io/bz2.sublime-package",
                                "sublime_text": "*",
                                "platforms": ["*"],
                                "python_versions": ["3.3"]
                            }
                        ]
                    }
                ),
                (
                    'ssl-linux',
                    {
                        "name": "ssl-linux",
                        "description": "Python _ssl module for Linux",
                        "author": "wbond",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-explicit.json'
                        ],
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "http://packagecontrol.io/ssl-linux.sublime-package",
                                "sublime_text": "*",
                                "platforms": ["linux"],
                                "python_versions": ["3.3"],
                                "sha256": "d12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4"
                            }
                        ]
                    }
                ),
                (
                    'ssl-windows',
                    {
                        "name": "ssl-windows",
                        "description": "Python _ssl module for Sublime Text 2 on Windows",
                        "author": "wbond",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-explicit.json'
                        ],
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "http://packagecontrol.io/ssl-windows.sublime-package",
                                "sublime_text": "<3000",
                                "platforms": ["windows"],
                                "python_versions": ["3.3"],
                                "sha256": "efe25e3bdf2e8f791d86327978aabe093c9597a6ceb8c2fb5438c1d810e02bea"
                            }
                        ]
                    }
                )
            ],
            list(provider.get_libraries())
        )

    def test_get_packages_300_github(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json'
            '/master/repository-3.0.0-github_releases.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    'package_control-tester-3.0.0-gh-tags',
                    {
                        "name": "package_control-tester-3.0.0-gh-tags",
                        "author": "packagecontrol-test",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-github_releases.json',
                            "https://github.com/packagecontrol-test/package_control-tester"
                        ],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-gh-tags_base',
                    {
                        "name": "package_control-tester-3.0.0-gh-tags_base",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        "readme": None,
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-github_releases.json'
                        ],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-gh-tags_prefix',
                    {
                        "name": "package_control-tester-3.0.0-gh-tags_prefix",
                        "author": "packagecontrol-test",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-github_releases.json',
                            "https://github.com/packagecontrol-test/package_control-tester"
                        ],
                        "last_modified": "2014-11-28 20:54:15",
                        "releases": [
                            {
                                "version": "1.0.2",
                                "date": "2014-11-28 20:54:15",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/win-1.0.2",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-gh-branch',
                    {
                        "name": "package_control-tester-3.0.0-gh-branch",
                        "author": "packagecontrol-test",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-github_releases.json',
                            "https://github.com/packagecontrol-test/package_control-tester"
                        ],
                        "last_modified": LAST_COMMIT_TIMESTAMP,
                        "releases": [
                            {
                                "version": LAST_COMMIT_VERSION,
                                "date": LAST_COMMIT_TIMESTAMP,
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/master",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages())
        )

    def test_get_packages_300_gitlab(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json'
            '/master/repository-3.0.0-gitlab_releases.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    'package_control-tester-3.0.0-gl-tags',
                    {
                        "name": "package_control-tester-3.0.0-gl-tags",
                        'author': 'packagecontrol-test',
                        'description': 'A test of Package Control upgrade messages with '
                                       'explicit versions, but date-based releases.',
                        'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                        'readme': 'https://gitlab.com/packagecontrol-test/'
                                  'package_control-tester/-/raw/master/readme.md',
                        'issues': None,
                        'donate': None,
                        'buy': None,
                        'sources': [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-gitlab_releases.json',
                            'https://gitlab.com/packagecontrol-test/package_control-tester'
                        ],
                        'labels': [],
                        'previous_names': [],
                        'last_modified': '2020-07-15 10:50:38',
                        'releases': [
                            {
                                "version": "1.0.1",
                                'date': '2020-07-15 10:50:38',
                                'url': 'https://gitlab.com/packagecontrol-test/'
                                       'package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip',
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-gl-tags_base',
                    {
                        "name": "package_control-tester-3.0.0-gl-tags_base",
                        'author': 'packagecontrol',
                        'description': 'A test of Package Control upgrade messages with '
                                       'explicit versions, but date-based releases.',
                        'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                        'readme': None,
                        'issues': None,
                        'donate': None,
                        'buy': None,
                        'sources': [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-gitlab_releases.json'
                        ],
                        'labels': [],
                        'previous_names': [],
                        'last_modified': '2020-07-15 10:50:38',
                        'releases': [
                            {
                                "version": "1.0.1",
                                'date': '2020-07-15 10:50:38',
                                'url': 'https://gitlab.com/packagecontrol-test/'
                                       'package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip',
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-gl-tags_prefix',
                    {
                        "name": "package_control-tester-3.0.0-gl-tags_prefix",
                        'author': 'packagecontrol-test',
                        'description': 'A test of Package Control upgrade messages with '
                                       'explicit versions, but date-based releases.',
                        'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                        'readme': 'https://gitlab.com/packagecontrol-test/'
                                  'package_control-tester/-/raw/master/readme.md',
                        'issues': None,
                        'donate': None,
                        'buy': None,
                        'sources': [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-gitlab_releases.json',
                            'https://gitlab.com/packagecontrol-test/package_control-tester'
                        ],
                        'labels': [],
                        'previous_names': [],
                        'last_modified': '2020-07-15 10:50:38',
                        'releases': [
                            {
                                "version": "1.0.1",
                                'date': '2020-07-15 10:50:38',
                                'url': 'https://gitlab.com/packagecontrol-test/'
                                       'package_control-tester/-/archive/win-1.0.1/'
                                       'package_control-tester-win-1.0.1.zip',
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-gl-branch',
                    {
                        'name': 'package_control-tester-3.0.0-gl-branch',
                        'description': 'A test of Package Control upgrade messages with '
                                       'explicit versions, but date-based releases.',
                        'homepage': 'https://gitlab.com/packagecontrol-test/package_control-tester',
                        'author': 'packagecontrol-test',
                        'readme': 'https://gitlab.com/packagecontrol-test/'
                                  'package_control-tester/-/raw/master/readme.md',
                        'issues': None,
                        'donate': None,
                        'buy': None,
                        'sources': [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-gitlab_releases.json',
                            'https://gitlab.com/packagecontrol-test/package_control-tester'
                        ],
                        'labels': [],
                        'previous_names': [],
                        'last_modified': '2020-07-15 10:50:38',
                        'releases': [
                            {
                                'date': '2020-07-15 10:50:38',
                                'version': '2020.07.15.10.50.38',
                                'url': 'https://gitlab.com/packagecontrol-test/'
                                       'package_control-tester/-/archive/master/'
                                       'package_control-tester-master.zip',
                                'sublime_text': '*',
                                'platforms': ['*']
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages())
        )

    def test_get_packages_300_bitbucket(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json'
            '/master/repository-3.0.0-bitbucket_releases.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    'package_control-tester-3.0.0-bb-tags',
                    {
                        "name": "package_control-tester-3.0.0-bb-tags",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-bitbucket_releases.json',
                            "https://bitbucket.org/wbond/package_control-tester"
                        ],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-bb-tags_prefix',
                    {
                        "name": "package_control-tester-3.0.0-bb-tags_prefix",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-bitbucket_releases.json',
                            "https://bitbucket.org/wbond/package_control-tester"
                        ],
                        "last_modified": "2014-11-28 20:54:15",
                        "releases": [
                            {
                                "version": "1.0.2",
                                "date": "2014-11-28 20:54:15",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/win-1.0.2.zip",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            }
                        ]
                    }
                ),
                (
                    'package_control-tester-3.0.0-bb-branch',
                    {
                        "name": "package_control-tester-3.0.0-bb-branch",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-3.0.0-bitbucket_releases.json',
                            "https://bitbucket.org/wbond/package_control-tester"
                        ],
                        "last_modified": LAST_COMMIT_TIMESTAMP,
                        "releases": [
                            {
                                "version": LAST_COMMIT_VERSION,
                                "date": LAST_COMMIT_TIMESTAMP,
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/master.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages())
        )

    def test_get_libraries_400_explicit(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-4.0.0-explicit.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    'bz2',
                    {
                        "name": "bz2",
                        "author": "wbond",
                        "description": "Python bz2 module",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-4.0.0-explicit.json'
                        ],
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "https://packagecontrol.io/bz2.sublime-package",
                                "sublime_text": "*",
                                "platforms": ["*"],
                                "python_versions": ["3.3"]
                            }
                        ]
                    }
                ),
                (
                    'ssl-linux',
                    {
                        "name": "ssl-linux",
                        "description": "Python _ssl module for Linux",
                        "author": "wbond",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "sources": [
                            'https://raw.githubusercontent.com/wbond/package_control-json'
                            '/master/repository-4.0.0-explicit.json'
                        ],
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "http://packagecontrol.io/ssl-linux.sublime-package",
                                "sublime_text": "*",
                                "platforms": ["linux"],
                                "python_versions": ["3.3", "3.8"],
                                "sha256": "d12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4"
                            }
                        ]
                    }
                ),
                # Note: 'ssl-windows' is expected to not be present because of missing python_versions!
            ],
            list(provider.get_libraries())
        )

    def test_get_packages_400_explicit(self):
        provider = JsonRepositoryProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/repository-4.0.0-explicit.json',
            self.settings()
        )
        self.assertEqual(
            [(
                'package_control-tester-4.0.0',
                {
                    "name": "package_control-tester-4.0.0",
                    "author": ["packagecontrol", "wbond"],
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                    "issues": None,
                    "donate": "https://gratipay.com/wbond/",
                    "buy": "https://example.com",
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": [
                        'https://raw.githubusercontent.com/wbond/package_control-json'
                        '/master/repository-4.0.0-explicit.json'
                    ],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"],
                            "libraries": ["bz2"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            list(provider.get_packages())
        )


class ChannelProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        return {
            'debug': DEBUG,
            'cache': HttpCache(604800),
            'cache_length': 604800,
            'user_agent': USER_AGENT,
            'http_basic_auth': {
                'raw.githubusercontent.com': [GH_USER, GH_PASS],
            }
        }

    def test_get_renamed_packages_12(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json',
            self.settings()
        )
        self.assertRaises(
            InvalidChannelFileException,
            provider.get_renamed_packages
        )

    def test_get_repositories_12(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json',
            self.settings()
        )
        self.assertRaises(
            InvalidChannelFileException,
            provider.get_repositories
        )

    def test_get_sources_12(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json',
            self.settings()
        )
        self.assertRaises(
            InvalidChannelFileException,
            provider.get_sources
        )

    def test_get_packages_12(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json',
            self.settings()
        )
        self.assertRaises(
            InvalidChannelFileException,
            list,
            provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json"
            )
        )

    def test_get_renamed_packages_20(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json',
            self.settings()
        )
        self.assertEqual(
            {},
            provider.get_renamed_packages()
        )

    def test_get_repositories_20(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-1.0.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-1.2.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-github_details.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-bitbucket_details.json"
            ],
            provider.get_repositories()
        )

    def test_get_sources_20(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-1.0.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-1.2.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-github_details.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-bitbucket_details.json"
            ],
            provider.get_sources()
        )

    def test_get_packages_20(self):
        self.maxDiff = None
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-1.0",
                    {
                        "name": "package_control-tester-1.0",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        "readme": None,
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2011-08-01 00:00:00",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2011-08-01 00:00:00",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2011-08-01 00:00:00",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2011-08-01 00:00:00",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-1.2",
                    {
                        "name": "package_control-tester-1.2",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        "readme": None,
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-2.0",
                    {
                        "name": "package_control-tester-2.0",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": "https://example.com",
                        "readme": None,
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "*",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "*",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-2.0-gh",
                    {
                        "name": "package_control-tester-2.0-gh",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-github_details.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-2.0-bb",
                    {
                        "name": "package_control-tester-2.0-bb",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-2.0-bitbucket_details.json"
            ))
        )

    def test_get_renamed_packages_300(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json',
            self.settings()
        )
        self.assertEqual(
            {},
            provider.get_renamed_packages()
        )

    def test_get_repositories_300(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-github_releases.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-gitlab_releases.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-bitbucket_releases.json"
            ],
            provider.get_repositories()
        )

    def test_get_sources_300(self):
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-github_releases.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-gitlab_releases.json",
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-bitbucket_releases.json"
            ],
            provider.get_sources()
        )

    def test_get_packages_300(self):
        self.maxDiff = None
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-3.0.0",
                    {
                        "name": "package_control-tester-3.0.0",
                        "author": ["packagecontrol", "wbond"],
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": "https://gratipay.com/wbond/",
                        "buy": "https://example.com",
                        "readme": None,
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "*",
                                "platforms": ["windows"],
                                "libraries": ["bz2"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "*",
                                "platforms": ["windows"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-3.0.0-gh-tags",
                    {
                        "name": "package_control-tester-3.0.0-gh-tags",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    "package_control-tester-3.0.0-gh-tags_base",
                    {
                        "name": "package_control-tester-3.0.0-gh-tags_base",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.1-beta",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/1.0.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/0.9.0",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    },
                ),
                (
                    "package_control-tester-3.0.0-gh-tags_prefix",
                    {
                        "name": "package_control-tester-3.0.0-gh-tags_prefix",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-28 20:54:15",
                        "releases": [
                            {
                                "version": "1.0.2",
                                "date": "2014-11-28 20:54:15",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/win-1.0.2",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            }
                        ]
                    }
                ),
                (
                    "package_control-tester-3.0.0-gh-branch",
                    {
                        "name": "package_control-tester-3.0.0-gh-branch",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                        "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                                  "/package_control-tester/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-28 20:54:15",
                        "releases": [
                            {
                                "version": "2014.11.28.20.54.15",
                                "date": "2014-11-28 20:54:15",
                                "url": "https://codeload.github.com/packagecontrol-test"
                                       "/package_control-tester/zip/master",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-github_releases.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-3.0.0-gl-tags",
                    {
                        "name": "package_control-tester-3.0.0-gl-tags",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        # Note:
                        # Shold be"https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md"
                        # Needs update of test data repository!
                        "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2020-07-15 10:50:38",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2020-07-15 10:50:38",
                                "url": "https://gitlab.com/packagecontrol-test"
                                       "/package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    "package_control-tester-3.0.0-gl-tags_base",
                    {
                        "name": "package_control-tester-3.0.0-gl-tags_base",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        # Note:
                        # Shold be"https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md"
                        # Needs update of test data repository!
                        "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2020-07-15 10:50:38",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2020-07-15 10:50:38",
                                "url": "https://gitlab.com/packagecontrol-test"
                                       "/package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                ),
                (
                    "package_control-tester-3.0.0-gl-tags_prefix",
                    {
                        "name": "package_control-tester-3.0.0-gl-tags_prefix",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        # Note:
                        # Shold be"https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md"
                        # Needs update of test data repository!
                        "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2020-07-15 10:50:38",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2020-07-15 10:50:38",
                                "url": "https://gitlab.com/packagecontrol-test"
                                       "/package_control-tester/-/archive/win-1.0.1"
                                       "/package_control-tester-win-1.0.1.zip",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            }
                        ]
                    }
                ),
                (
                    "package_control-tester-3.0.0-gl-branch",
                    {
                        "name": "package_control-tester-3.0.0-gl-branch",
                        "author": "packagecontrol",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                        "issues": None,
                        "donate": None,
                        "buy": None,
                        # Note:
                        # Shold be"https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md"
                        # Needs update of test data repository!
                        "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2020-07-15 10:50:38",
                        "releases": [
                            {
                                "version": "2020.07.15.10.50.38",
                                "date": "2020-07-15 10:50:38",
                                "url": "https://gitlab.com/packagecontrol-test"
                                       "/package_control-tester/-/archive/master/package_control-tester-master.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-gitlab_releases.json"
            ))
        )
        self.assertEqual(
            [
                (
                    "package_control-tester-3.0.0-bb-tags",
                    {
                        "name": "package_control-tester-3.0.0-bb-tags",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-12 15:52:35",
                        "releases": [
                            {
                                "version": "1.0.1",
                                "date": "2014-11-12 15:52:35",
                                "url": "https://bitbucket.org/wbond/package_control-tester"
                                       "/get/1.0.1.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.1-beta",
                                "date": "2014-11-12 15:14:23",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "1.0.0",
                                "date": "2014-11-12 15:14:13",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            },
                            {
                                "version": "0.9.0",
                                "date": "2014-11-12 02:02:22",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip",
                                "sublime_text": "<3000",
                                "platforms": ["*"]
                            }
                        ]
                    },
                ),
                (
                    "package_control-tester-3.0.0-bb-tags_prefix",
                    {
                        "name": "package_control-tester-3.0.0-bb-tags_prefix",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-28 20:54:15",
                        "releases": [
                            {
                                "version": "1.0.2",
                                "date": "2014-11-28 20:54:15",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/win-1.0.2.zip",
                                "sublime_text": "<3000",
                                "platforms": ["windows"]
                            }
                        ]
                    },
                ),
                (
                    "package_control-tester-3.0.0-bb-branch",
                    {
                        "name": "package_control-tester-3.0.0-bb-branch",
                        "author": "wbond",
                        "description": "A test of Package Control upgrade messages with "
                                       "explicit versions, but date-based releases.",
                        "homepage": "https://bitbucket.org/wbond/package_control-tester",
                        "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                        "donate": None,
                        "buy": None,
                        "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                        "previous_names": [],
                        "labels": [],
                        "last_modified": "2014-11-28 20:54:15",
                        "releases": [
                            {
                                "version": "2014.11.28.20.54.15",
                                "date": "2014-11-28 20:54:15",
                                "url": "https://bitbucket.org/wbond/package_control-tester/get/master.zip",
                                "sublime_text": "*",
                                "platforms": ["*"]
                            }
                        ]
                    }
                )
            ],
            list(provider.get_packages(
                "https://raw.githubusercontent.com/wbond/package_control-json"
                "/master/repository-3.0.0-bitbucket_releases.json"
            ))
        )

    def test_get_libraries_300(self):
        self.maxDiff = None
        provider = ChannelProvider(
            'https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json',
            self.settings()
        )
        self.assertEqual(
            [
                (
                    'bz2',
                    {
                        "name": "bz2",
                        "author": "wbond",
                        "description": "Python bz2 module",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "https://packagecontrol.io/bz2.sublime-package",
                                "sublime_text": "*",
                                "platforms": ["*"],
                                "python_versions": ["3.3"]

                            }
                        ]
                    },
                ),
                (
                    'ssl-linux',
                    {
                        "name": "ssl-linux",
                        "description": "Python _ssl module for Linux",
                        "author": "wbond",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "http://packagecontrol.io/ssl-linux.sublime-package",
                                "sublime_text": "*",
                                "platforms": ["linux"],
                                "python_versions": ["3.3"],
                                "sha256": "d12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4"
                            }
                        ]
                    },
                ),
                (
                    'ssl-windows',
                    {
                        "name": "ssl-windows",
                        "description": "Python _ssl module for Sublime Text 2 on Windows",
                        "author": "wbond",
                        "issues": "https://github.com/wbond/package_control/issues",
                        "releases": [
                            {
                                "version": "1.0.0",
                                "url": "http://packagecontrol.io/ssl-windows.sublime-package",
                                "sublime_text": "<3000",
                                "platforms": ["windows"],
                                "python_versions": ["3.3"],
                                "sha256": "efe25e3bdf2e8f791d86327978aabe093c9597a6ceb8c2fb5438c1d810e02bea"
                            }
                        ]
                    }
                )
            ],
            list(provider.get_libraries(
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json"
            ))
        )
