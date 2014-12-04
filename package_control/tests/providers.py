import unittest

from ..providers.repository_provider import RepositoryProvider
from ..providers.channel_provider import ChannelProvider
from ..providers.github_repository_provider import GitHubRepositoryProvider
from ..providers.github_user_provider import GitHubUserProvider
from ..providers.bitbucket_repository_provider import BitBucketRepositoryProvider
from ..http_cache import HttpCache

from . import LAST_COMMIT_TIMESTAMP, LAST_COMMIT_VERSION, CLIENT_ID, CLIENT_SECRET


class GitHubRepositoryProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(True, GitHubRepositoryProvider.match_url('https://github.com/packagecontrol/package_control-tester'))
        self.assertEqual(True, GitHubRepositoryProvider.match_url('https://github.com/packagecontrol/package_control-tester/tree/master'))
        self.assertEqual(False, GitHubRepositoryProvider.match_url('https://github.com/packagecontrol'))

    def test_get_packages(self):
        provider = GitHubRepositoryProvider('https://github.com/packagecontrol/package_control-tester', self.github_settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester',
                {
                    'name': 'package_control-tester',
                    'description': 'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                    'homepage': 'https://github.com/packagecontrol/package_control-tester',
                    'author': 'packagecontrol',
                    'readme': 'https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md',
                    'issues': 'https://github.com/packagecontrol/package_control-tester/issues',
                    'donate': 'https://gratipay.com/on/github/packagecontrol/',
                    'buy': None,
                    'sources': ['https://github.com/packagecontrol/package_control-tester'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [
                        {
                            'date': LAST_COMMIT_TIMESTAMP,
                            'version': LAST_COMMIT_VERSION,
                            'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/master',
                            'sublime_text': '*',
                            'platforms': ['*']
                        }
                    ],
                    'last_modified': LAST_COMMIT_TIMESTAMP
                }
            )],
            packages
        )

    def test_get_sources(self):
        provider = GitHubRepositoryProvider('https://github.com/packagecontrol/package_control-tester', self.github_settings())
        self.assertEqual(['https://github.com/packagecontrol/package_control-tester'], provider.get_sources())

    def test_get_renamed_packages(self):
        provider = GitHubRepositoryProvider('https://github.com/packagecontrol/package_control-tester', self.github_settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = GitHubRepositoryProvider('https://github.com/packagecontrol/package_control-tester', self.github_settings())
        self.assertEqual(list(), list(provider.get_broken_packages()))

    def test_get_dependencies(self):
        provider = GitHubRepositoryProvider('https://github.com/packagecontrol/package_control-tester', self.github_settings())
        self.assertEqual(list(), list(provider.get_dependencies()))

    def test_get_broken_dependencies(self):
        provider = GitHubRepositoryProvider('https://github.com/packagecontrol/package_control-tester', self.github_settings())
        self.assertEqual(list(), list(provider.get_broken_dependencies()))


class GitHubUserProviderTests(unittest.TestCase):
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

    def test_match_url(self):
        self.assertEqual(True, GitHubUserProvider.match_url('https://github.com/packagecontrol'))
        self.assertEqual(False, GitHubUserProvider.match_url('https://github.com/packagecontrol/package_control-tester/tree/master'))
        self.assertEqual(False, GitHubUserProvider.match_url('https://bitbucket.org/packagecontrol'))

    def test_get_packages(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol', self.github_settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester',
                {
                    'name': 'package_control-tester',
                    'description': 'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                    'homepage': 'https://github.com/packagecontrol/package_control-tester',
                    'author': 'packagecontrol',
                    'readme': 'https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md',
                    'issues': 'https://github.com/packagecontrol/package_control-tester/issues',
                    'donate': 'https://gratipay.com/on/github/packagecontrol/',
                    'buy': None,
                    'sources': ['https://github.com/packagecontrol'],
                    'labels': [],
                    'previous_names': [],
                    'releases': [
                        {
                            'date': LAST_COMMIT_TIMESTAMP,
                            'version': LAST_COMMIT_VERSION,
                            'url': 'https://codeload.github.com/packagecontrol/package_control-tester/zip/master',
                            'sublime_text': '*',
                            'platforms': ['*']
                        }
                    ],
                    'last_modified': LAST_COMMIT_TIMESTAMP
                }
            )],
            packages
        )

    def test_get_sources(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol', self.github_settings())
        self.assertEqual(['https://github.com/packagecontrol'], provider.get_sources())

    def test_get_renamed_packages(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol', self.github_settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol', self.github_settings())
        self.assertEqual(list(), list(provider.get_broken_packages()))

    def test_get_dependencies(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol', self.github_settings())
        self.assertEqual(list(), list(provider.get_dependencies()))

    def test_get_broken_dependencies(self):
        provider = GitHubUserProvider('https://github.com/packagecontrol', self.github_settings())
        self.assertEqual(list(), list(provider.get_broken_dependencies()))


class BitBucketRepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def bitbucket_settings(self):
        return {
            'debug': True,
            'cache': HttpCache(604800)
        }

    def test_match_url(self):
        self.assertEqual(True, BitBucketRepositoryProvider.match_url('https://bitbucket.org/wbond/package_control-tester'))
        self.assertEqual(False, BitBucketRepositoryProvider.match_url('https://bitbucket.org/wbond'))
        self.assertEqual(False, BitBucketRepositoryProvider.match_url('https://github.com/wbond/package_control-tester'))

    def test_get_packages(self):
        provider = BitBucketRepositoryProvider('https://bitbucket.org/wbond/package_control-tester', self.bitbucket_settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester',
                {
                    'name': 'package_control-tester',
                    'description': 'A test of Package Control upgrade messages with explicit versions, but date-based releases.',
                    'homepage': 'https://bitbucket.org/wbond/package_control-tester',
                    'author': 'wbond',
                    'readme': 'https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md',
                    'issues': 'https://bitbucket.org/wbond/package_control-tester/issues',
                    'donate': 'https://gratipay.com/on/bitbucket/wbond/',
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
            packages
        )

    def test_get_sources(self):
        provider = BitBucketRepositoryProvider('https://bitbucket.org/wbond/package_control-tester', self.bitbucket_settings())
        self.assertEqual(['https://bitbucket.org/wbond/package_control-tester'], provider.get_sources())

    def test_get_renamed_packages(self):
        provider = BitBucketRepositoryProvider('https://bitbucket.org/wbond/package_control-tester', self.bitbucket_settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_broken_packages(self):
        provider = BitBucketRepositoryProvider('https://bitbucket.org/wbond/package_control-tester', self.bitbucket_settings())
        self.assertEqual(list(), list(provider.get_broken_packages()))

    def test_get_dependencies(self):
        provider = BitBucketRepositoryProvider('https://bitbucket.org/wbond/package_control-tester', self.bitbucket_settings())
        self.assertEqual(list(), list(provider.get_dependencies()))

    def test_get_broken_dependencies(self):
        provider = BitBucketRepositoryProvider('https://bitbucket.org/wbond/package_control-tester', self.bitbucket_settings())
        self.assertEqual(list(), list(provider.get_broken_dependencies()))


class RepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        return {
            'debug': True,
            'cache': HttpCache(604800)
        }

    def test_get_packages_10(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-1.0',
                {
                    "name": "package_control-tester-1.0",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": None,
                    "donate": None,
                    "buy": None,
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json'],
                    "last_modified": "2011-08-01 00:00:00",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            packages
        )

    def test_get_dependencies_10(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json', self.settings())
        dependencies = [dependency for dependency in provider.get_dependencies()]
        self.assertEqual([], dependencies)

    def test_get_packages_12(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-1.2',
                {
                    "name": "package_control-tester-1.2",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": None,
                    "donate": None,
                    "buy": None,
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json'],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            packages
        )

    def test_get_dependencies_12(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json', self.settings())
        dependencies = [dependency for dependency in provider.get_dependencies()]
        self.assertEqual([], dependencies)

    def test_get_packages_20_explicit(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-2.0',
                {
                    "name": "package_control-tester-2.0",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": None,
                    "donate": None,
                    "buy": "https://example.com",
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json'],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            packages
        )

    def test_get_dependencies_20(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json', self.settings())
        dependencies = [dependency for dependency in provider.get_dependencies()]
        self.assertEqual([], dependencies)

    def test_get_packages_20_github(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-github_details.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-2.0-gh',
                {
                    "name": "package_control-tester-2.0-gh",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-github_details.json', "https://github.com/packagecontrol/package_control-tester"],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            packages
        )

    def test_get_packages_20_bitbucket(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-bitbucket_details.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-2.0-bb',
                {
                    "name": "package_control-tester-2.0-bb",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
                    "buy": None,
                    "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-bitbucket_details.json', "https://bitbucket.org/wbond/package_control-tester"],
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
            packages
        )

    def test_get_packages_300_explicit(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-3.0.0',
                {
                    "name": "package_control-tester-3.0.0",
                    "author": ["packagecontrol", "wbond"],
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": None,
                    "donate": None,
                    "buy": "https://example.com",
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json'],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"],
                            "dependencies": ["bz2"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            packages
        )

    def test_get_dependencies_300_explicit(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json', self.settings())
        dependencies = [dependency for dependency in provider.get_dependencies()]
        self.assertEqual(
            [(
                'bz2',
                {
                    "name": "bz2",
                    "load_order": "02",
                    "author": "wbond",
                    "description": "Python bz2 module",
                    "issues": "https://github.com/wbond/package_control/issues",
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json'],
                    "releases": [
                        {
                            "version": "1.0.0",
                            "url": "https://packagecontrol.io/bz2.sublime-package",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ]
                }
            ),
            (
                'ssl-linux',
                {
                    "name": "ssl-linux",
                    "load_order": "01",
                    "description": "Python _ssl module for Linux",
                    "author": "wbond",
                    "issues": "https://github.com/wbond/package_control/issues",
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json'],
                    "releases": [
                        {
                            "version": "1.0.0",
                            "url": "http://packagecontrol.io/ssl-linux.sublime-package",
                            "sublime_text": "*",
                            "platforms": ["linux"],
                            "sha256": "d12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4"
                        }
                    ]
                }
            ),
            (
                'ssl-windows',
                {
                    "name": "ssl-windows",
                    "load_order": "01",
                    "description": "Python _ssl module for Sublime Text 2 on Windows",
                    "author": "wbond",
                    "issues": "https://github.com/wbond/package_control/issues",
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json'],
                    "releases": [
                        {
                            "version": "1.0.0",
                            "url": "http://packagecontrol.io/ssl-windows.sublime-package",
                            "sublime_text": "<3000",
                            "platforms": ["windows"],
                            "sha256": "efe25e3bdf2e8f791d86327978aabe093c9597a6ceb8c2fb5438c1d810e02bea"
                        }
                    ]
                }
            )],
            dependencies
        )

    def test_get_packages_300_github(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-3.0.0-gh-tags',
                {
                    "name": "package_control-tester-3.0.0-gh-tags",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json', "https://github.com/packagecontrol/package_control-tester"],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
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
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": None,
                    "donate": None,
                    "buy": None,
                    "readme": None,
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json'],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
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
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json', "https://github.com/packagecontrol/package_control-tester"],
                    "last_modified": "2014-11-28 20:54:15",
                    "releases": [
                        {
                            "version": "1.0.2",
                            "date": "2014-11-28 20:54:15",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/win-1.0.2",
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
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json', "https://github.com/packagecontrol/package_control-tester"],
                    "last_modified": LAST_COMMIT_TIMESTAMP,
                    "releases": [
                        {
                            "version": LAST_COMMIT_VERSION,
                            "date": LAST_COMMIT_TIMESTAMP,
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/master",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ]
                }
            )],
            packages
        )

    def test_get_packages_300_bitbucket(self):
        provider = RepositoryProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json', self.settings())
        packages = [package for package in provider.get_packages()]
        self.assertEqual(
            [(
                'package_control-tester-3.0.0-bb-tags',
                {
                    "name": "package_control-tester-3.0.0-bb-tags",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
                    "buy": None,
                    "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json', "https://bitbucket.org/wbond/package_control-tester"],
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
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
                    "buy": None,
                    "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json', "https://bitbucket.org/wbond/package_control-tester"],
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
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
                    "buy": None,
                    "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "sources": ['https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json', "https://bitbucket.org/wbond/package_control-tester"],
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
            )],
            packages
        )


class ChannelProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        return {
            'debug': True,
            'cache': HttpCache(604800)
        }

    def test_get_name_map_12(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json', self.settings())
        self.assertEqual(
            {},
            provider.get_name_map()
        )

    def test_get_renamed_packages_12(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json', self.settings())
        self.assertEqual(
            {},
            provider.get_renamed_packages()
        )

    def test_get_repositories_12(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json', self.settings())
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json"
            ],
            provider.get_repositories()
        )

    def test_get_sources_12(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json', self.settings())
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json"
            ],
            provider.get_sources()
        )

    def test_get_packages_12(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-1.2.json', self.settings())
        self.assertEqual(
            {
                "package_control-tester-1.0": {
                    "name": "package_control-tester-1.0",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
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
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json")
        )
        self.assertEqual(
            {
                "package_control-tester-1.2": {
                    "name": "package_control-tester-1.2",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
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
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json")
        )

    def test_get_name_map_20(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json', self.settings())
        self.assertEqual(
            {},
            provider.get_name_map()
        )

    def test_get_renamed_packages_20(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json', self.settings())
        self.assertEqual(
            {},
            provider.get_renamed_packages()
        )

    def test_get_repositories_20(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json', self.settings())
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-github_details.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-bitbucket_details.json"
            ],
            provider.get_repositories()
        )

    def test_get_sources_20(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json', self.settings())
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-github_details.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-bitbucket_details.json"
            ],
            provider.get_sources()
        )

    def test_get_packages_20(self):
        self.maxDiff = None
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-2.0.json', self.settings())
        self.assertEqual(
            {
                "package_control-tester-1.0": {
                    "name": "package_control-tester-1.0",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
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
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2011-08-01 00:00:00",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.0.json")
        )
        self.assertEqual(
            {
                "package_control-tester-1.2": {
                    "name": "package_control-tester-1.2",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
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
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-1.2.json")
        )
        self.assertEqual(
            {
                "package_control-tester-2.0": {
                    "name": "package_control-tester-2.0",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
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
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-explicit.json")
        )
        self.assertEqual(
            {
                "package_control-tester-2.0-gh": {
                    "name": "package_control-tester-2.0-gh",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-github_details.json")
        )
        self.assertEqual(
            {
                "package_control-tester-2.0-bb": {
                    "name": "package_control-tester-2.0-bb",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
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
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-2.0-bitbucket_details.json")
        )

    def test_get_name_map_300(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json', self.settings())
        self.assertEqual(
            {},
            provider.get_name_map()
        )

    def test_get_renamed_packages_300(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json', self.settings())
        self.assertEqual(
            {},
            provider.get_renamed_packages()
        )

    def test_get_repositories_300(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json', self.settings())
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json"
            ],
            provider.get_repositories()
        )

    def test_get_sources_300(self):
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json', self.settings())
        self.assertEqual(
            [
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json",
                "https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json"
            ],
            provider.get_sources()
        )

    def test_get_packages_300(self):
        self.maxDiff = None
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json', self.settings())
        self.assertEqual(
            {
                "package_control-tester-3.0.0": {
                    "name": "package_control-tester-3.0.0",
                    "author": ["packagecontrol", "wbond"],
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
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
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "*",
                            "platforms": ["windows"],
                            "dependencies": ["bz2"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "*",
                            "platforms": ["windows"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json")
        )
        self.assertEqual(
            {
                "package_control-tester-3.0.0-gh-tags": {
                    "name": "package_control-tester-3.0.0-gh-tags",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                },
                "package_control-tester-3.0.0-gh-tags_base": {
                    "name": "package_control-tester-3.0.0-gh-tags_base",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "last_modified": "2014-11-12 15:52:35",
                    "releases": [
                        {
                            "version": "1.0.1",
                            "date": "2014-11-12 15:52:35",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.1-beta",
                            "date": "2014-11-12 15:14:23",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.1-beta",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "1.0.0",
                            "date": "2014-11-12 15:14:13",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/1.0.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        },
                        {
                            "version": "0.9.0",
                            "date": "2014-11-12 02:02:22",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/0.9.0",
                            "sublime_text": "<3000",
                            "platforms": ["*"]
                        }
                    ]
                },
                "package_control-tester-3.0.0-gh-tags_prefix": {
                    "name": "package_control-tester-3.0.0-gh-tags_prefix",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "last_modified": "2014-11-28 20:54:15",
                    "releases": [
                        {
                            "version": "1.0.2",
                            "date": "2014-11-28 20:54:15",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/win-1.0.2",
                            "sublime_text": "<3000",
                            "platforms": ["windows"]
                        }
                    ]
                },
                "package_control-tester-3.0.0-gh-branch": {
                    "name": "package_control-tester-3.0.0-gh-branch",
                    "author": "packagecontrol",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol/package_control-tester",
                    "issues": "https://github.com/packagecontrol/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/github/packagecontrol/",
                    "buy": None,
                    "readme": "https://raw.githubusercontent.com/packagecontrol/package_control-tester/master/readme.md",
                    "previous_names": [],
                    "labels": [],
                    "last_modified": "2014-11-28 20:54:15",
                    "releases": [
                        {
                            "version": "2014.11.28.20.54.15",
                            "date": "2014-11-28 20:54:15",
                            "url": "https://codeload.github.com/packagecontrol/package_control-tester/zip/master",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ]
                }
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-github_releases.json")
        )
        self.assertEqual(
            {
                "package_control-tester-3.0.0-bb-tags": {
                    "name": "package_control-tester-3.0.0-bb-tags",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
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
                },
                "package_control-tester-3.0.0-bb-tags_prefix": {
                    "name": "package_control-tester-3.0.0-bb-tags_prefix",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
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
                "package_control-tester-3.0.0-bb-branch": {
                    "name": "package_control-tester-3.0.0-bb-branch",
                    "author": "wbond",
                    "description": "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": "https://gratipay.com/on/bitbucket/wbond/",
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
            },
            provider.get_packages("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-bitbucket_releases.json")
        )

    def test_get_dependencies_300(self):
        self.maxDiff = None
        provider = ChannelProvider('https://raw.githubusercontent.com/wbond/package_control-json/master/channel-3.0.0.json', self.settings())
        self.assertEqual(
            {
                'bz2': {
                    "name": "bz2",
                    "load_order": "02",
                    "author": "wbond",
                    "description": "Python bz2 module",
                    "issues": "https://github.com/wbond/package_control/issues",
                    "releases": [
                        {
                            "version": "1.0.0",
                            "url": "https://packagecontrol.io/bz2.sublime-package",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ]
                },
                'ssl-linux': {
                    "name": "ssl-linux",
                    "load_order": "01",
                    "description": "Python _ssl module for Linux",
                    "author": "wbond",
                    "issues": "https://github.com/wbond/package_control/issues",
                    "releases": [
                        {
                            "version": "1.0.0",
                            "url": "http://packagecontrol.io/ssl-linux.sublime-package",
                            "sublime_text": "*",
                            "platforms": ["linux"],
                            "sha256": "d12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4"
                        }
                    ]
                },
                'ssl-windows': {
                    "name": "ssl-windows",
                    "load_order": "01",
                    "description": "Python _ssl module for Sublime Text 2 on Windows",
                    "author": "wbond",
                    "issues": "https://github.com/wbond/package_control/issues",
                    "releases": [
                        {
                            "version": "1.0.0",
                            "url": "http://packagecontrol.io/ssl-windows.sublime-package",
                            "sublime_text": "<3000",
                            "platforms": ["windows"],
                            "sha256": "efe25e3bdf2e8f791d86327978aabe093c9597a6ceb8c2fb5438c1d810e02bea"
                        }
                    ]
                }
            },
            provider.get_dependencies("https://raw.githubusercontent.com/wbond/package_control-json/master/repository-3.0.0-explicit.json")
        )
