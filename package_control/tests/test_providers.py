# flake8: noqa: E501

import unittest

from ..http_cache import HttpCache
from ..providers.bitbucket_repository_provider import BitBucketRepositoryProvider
from ..providers.channel_provider import ChannelProvider, InvalidChannelFileException
from ..providers.github_repository_provider import GitHubRepositoryProvider
from ..providers.github_user_provider import GitHubUserProvider
from ..providers.gitlab_repository_provider import GitLabRepositoryProvider
from ..providers.gitlab_user_provider import GitLabUserProvider
from ..providers.json_repository_provider import JsonRepositoryProvider
from ..providers import json_repository_provider
from ._data_decorator import data_decorator, data

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

# URL to repository with test data (channels, repositories)
TEST_REPOSITORY_URL = "https://raw.githubusercontent.com/wbond/package_control-json/master/"

# prevent optimizations when running tests those
# filter out required results for platform independent tests.
json_repository_provider.IS_ST = False


@data_decorator
class BitBucketRepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        if not BB_PASS:
            self.skipTest("BitBucket app password for %s not set via env var BB_PASS" % BB_USER)

        return {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "api.bitbucket.org": [BB_USER, BB_PASS]
            }
        }

    @data(
        (
            ("https://bitbucket.org/wbond/package_control-tester", True),
            ("https://bitbucket.org/wbond/package_control-tester/", True),
            ("https://bitbucket.org/wbond/package_control-tester/src/master", True),
            ("https://bitbucket.org/wbond", False),
            ("https://bitbucket,org/wbond/package_control-tester", False),
            ("https://github.com/wbond/package_control-tester", False),
            ("https://gitlab.com/wbond/package_control-tester", False)
        )
    )
    def match_url(self, url, result):
        self.assertEqual(result, BitBucketRepositoryProvider.match_url(url))

    def test_get_libraries(self):
        provider = BitBucketRepositoryProvider(
            "https://bitbucket.org/wbond/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = BitBucketRepositoryProvider(
            "https://bitbucket.org/wbond/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_broken_libraries()))

    def test_get_packages(self):
        provider = BitBucketRepositoryProvider(
            "https://bitbucket.org/wbond/package_control-tester",
            self.settings()
        )
        self.assertEqual(
            [(
                "package_control-tester",
                {
                    "name": "package_control-tester",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://bitbucket.org/wbond/package_control-tester",
                    "author": "wbond",
                    "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                    "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                    "donate": None,
                    "buy": None,
                    "sources": ["https://bitbucket.org/wbond/package_control-tester"],
                    "labels": [],
                    "previous_names": [],
                    "releases": [
                        {
                            "date": LAST_COMMIT_TIMESTAMP,
                            "version": LAST_COMMIT_VERSION,
                            "url": "https://bitbucket.org/wbond/package_control-tester/get/master.zip",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ],
                    "last_modified": LAST_COMMIT_TIMESTAMP
                }
            )],
            list(provider.get_packages())
        )

    def test_get_broken_packages(self):
        provider = BitBucketRepositoryProvider(
            "https://bitbucket.org/wbond/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_renamed_packages(self):
        provider = BitBucketRepositoryProvider(
            "https://bitbucket.org/wbond/package_control-tester",
            self.settings()
        )
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_sources(self):
        provider = BitBucketRepositoryProvider(
            "https://bitbucket.org/wbond/package_control-tester",
            self.settings()
        )
        self.assertEqual(
            ["https://bitbucket.org/wbond/package_control-tester"],
            provider.get_sources()
        )


@data_decorator
class GitHubRepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        if not GH_PASS:
            self.skipTest("GitHub personal access token for %s not set via env var GH_PASS" % GH_USER)

        return {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "api.github.com": [GH_USER, GH_PASS],
                "raw.githubusercontent.com": [GH_USER, GH_PASS],
            }
        }

    @data(
        (
            ("https://github.com/packagecontrol-test/package_control-tester", True),
            ("https://github.com/packagecontrol-test/package_control-tester/", True),
            ("https://github.com/packagecontrol-test/package_control-tester/tree/master", True),
            ("https://github.com/packagecontrol-test", False),
            ("https://github,com/packagecontrol-test/package_control-tester", False),
            ("https://gitlab.com/packagecontrol-test/package_control-tester", False),
            ("https://bitbucket.org/wbond/package_control-tester", False)
        )
    )
    def match_url(self, url, result):
        self.assertEqual(result, GitHubRepositoryProvider.match_url(url))

    def test_get_libraries(self):
        provider = GitHubRepositoryProvider(
            "https://github.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitHubRepositoryProvider(
            "https://github.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_broken_libraries()))

    def test_get_packages(self):
        provider = GitHubRepositoryProvider(
            "https://github.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual(
            [(
                "package_control-tester",
                {
                    "name": "package_control-tester",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                    "author": "packagecontrol-test",
                    "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                              "/package_control-tester/master/readme.md",
                    "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                    "donate": None,
                    "buy": None,
                    "sources": ["https://github.com/packagecontrol-test/package_control-tester"],
                    "labels": [],
                    "previous_names": [],
                    "releases": [
                        {
                            "date": LAST_COMMIT_TIMESTAMP,
                            "version": LAST_COMMIT_VERSION,
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/master",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ],
                    "last_modified": LAST_COMMIT_TIMESTAMP
                }
            )],
            list(provider.get_packages())
        )

    def test_get_broken_packages(self):
        provider = GitHubRepositoryProvider(
            "https://github.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_renamed_packages(self):
        provider = GitHubRepositoryProvider(
            "https://github.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_sources(self):
        provider = GitHubRepositoryProvider(
            "https://github.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual(
            ["https://github.com/packagecontrol-test/package_control-tester"],
            provider.get_sources()
        )


@data_decorator
class GitHubUserProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        if not GH_PASS:
            self.skipTest("GitHub personal access token for %s not set via env var GH_PASS" % GH_USER)

        return {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "api.github.com": [GH_USER, GH_PASS],
                "raw.githubusercontent.com": [GH_USER, GH_PASS],
            }
        }

    @data(
        (
            ("https://github.com/packagecontrol-test", True),
            ("https://github.com/packagecontrol-test/", True),
            ("https://github,com/packagecontrol-test", False),
            ("https://github.com/packagecontrol-test/package_control-tester", False),
            ("https://github.com/packagecontrol-test/package_control-tester/tree/master", False),
            ("https://bitbucket.org/packagecontrol-test", False),
        )
    )
    def match_url(self, url, result):
        self.assertEqual(result, GitHubUserProvider.match_url(url))

    def test_get_libraries(self):
        provider = GitHubUserProvider("https://github.com/packagecontrol-test", self.settings())
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitHubUserProvider("https://github.com/packagecontrol-test", self.settings())
        self.assertEqual([], list(provider.get_broken_libraries()))

    def test_get_packages(self):
        provider = GitHubUserProvider("https://github.com/packagecontrol-test", self.settings())
        self.assertEqual(
            [(
                "package_control-tester",
                {
                    "name": "package_control-tester",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                    "author": "packagecontrol-test",
                    "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                              "/package_control-tester/master/readme.md",
                    "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                    "donate": None,
                    "buy": None,
                    "sources": ["https://github.com/packagecontrol-test"],
                    "labels": [],
                    "previous_names": [],
                    "releases": [
                        {
                            "date": LAST_COMMIT_TIMESTAMP,
                            "version": LAST_COMMIT_VERSION,
                            "url": "https://codeload.github.com/packagecontrol-test"
                                   "/package_control-tester/zip/master",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ],
                    "last_modified": LAST_COMMIT_TIMESTAMP
                }
            )],
            list(provider.get_packages())
        )

    def test_get_broken_packages(self):
        provider = GitHubUserProvider("https://github.com/packagecontrol-test", self.settings())
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_renamed_packages(self):
        provider = GitHubUserProvider("https://github.com/packagecontrol-test", self.settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_sources(self):
        provider = GitHubUserProvider("https://github.com/packagecontrol-test", self.settings())
        self.assertEqual(["https://github.com/packagecontrol-test"], provider.get_sources())


@data_decorator
class GitLabRepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        if not GL_PASS:
            self.skipTest("GitLab personal access token for %s not set via env var GL_PASS" % GL_USER)

        return {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "gitlab.com": [GL_USER, GL_PASS]
            }
        }

    @data(
        (
            ("https://gitlab.com/packagecontrol-test/package_control-tester", True),
            ("https://gitlab.com/packagecontrol-test/package_control-tester/", True),
            ("https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master", True),
            ("https://gitlab.com/packagecontrol-test", False),
            ("https://gitlab,com/packagecontrol-test/package_control-tester", False),
            ("https://github.com/packagecontrol-test/package_control-tester", False),
            ("https://bitbucket.org/wbond/package_control-tester", False)
        )
    )
    def match_url(self, url, result):
        self.assertEqual(result, GitLabRepositoryProvider.match_url(url))

    def test_get_libraries(self):
        provider = GitLabRepositoryProvider(
            "https://gitlab.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitLabRepositoryProvider(
            "https://gitlab.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_broken_libraries()))

    def test_get_packages(self):
        provider = GitLabRepositoryProvider(
            "https://gitlab.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual(
            [(
                "package_control-tester",
                {
                    "name": "package_control-tester",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                    "author": "packagecontrol-test",
                    "readme": "https://gitlab.com/packagecontrol-test/"
                              "package_control-tester/-/raw/master/readme.md",
                    "issues": None,
                    "donate": None,
                    "buy": None,
                    "sources": ["https://gitlab.com/packagecontrol-test/package_control-tester"],
                    "labels": [],
                    "previous_names": [],
                    "releases": [
                        {
                            "date": "2020-07-15 10:50:38",
                            "version": "2020.07.15.10.50.38",
                            "url": "https://gitlab.com/packagecontrol-test/"
                                   "package_control-tester/-/archive/master/"
                                   "package_control-tester-master.zip",
                            "sublime_text": "*",
                            "platforms": ["*"]
                        }
                    ],
                    "last_modified": "2020-07-15 10:50:38"
                }
            )],
            list(provider.get_packages())
        )

    def test_get_broken_packages(self):
        provider = GitLabRepositoryProvider(
            "https://gitlab.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_renamed_packages(self):
        provider = GitLabRepositoryProvider(
            "https://gitlab.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_sources(self):
        provider = GitLabRepositoryProvider(
            "https://gitlab.com/packagecontrol-test/package_control-tester",
            self.settings()
        )
        self.assertEqual(
            ["https://gitlab.com/packagecontrol-test/package_control-tester"],
            provider.get_sources()
        )


@data_decorator
class GitLabUserProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        if not GL_PASS:
            self.skipTest("GitLab personal access token for %s not set via env var GL_PASS" % GL_USER)

        return {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "gitlab.com": [GL_USER, GL_PASS]
            }
        }

    @data(
        (
            ("https://gitlab.com/packagecontrol-test", True),
            ("https://gitlab.com/packagecontrol-test/", True),
            ("https://gitlab,com/packagecontrol-test", False),
            ("https://gitlab.com/packagecontrol-test/package_control-tester", False),
            ("https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master", False),
            ("https://bitbucket.org/packagecontrol-test", False),
        )
    )
    def match_url(self, url, result):
        self.assertEqual(result, GitLabUserProvider.match_url(url))

    def test_get_libraries(self):
        provider = GitLabUserProvider("https://gitlab.com/packagecontrol-test", self.settings())
        self.assertEqual([], list(provider.get_libraries()))

    def test_get_broken_libraries(self):
        provider = GitLabUserProvider("https://gitlab.com/packagecontrol-test", self.settings())
        self.assertEqual([], list(provider.get_broken_libraries()))

    def test_get_packages(self):
        provider = GitLabUserProvider("https://gitlab.com/packagecontrol-test", self.settings())
        self.assertEqual(
            [(
                "package_control-tester",
                {
                    "name": "package_control-tester",
                    "description": "A test of Package Control upgrade messages with "
                                   "explicit versions, but date-based releases.",
                    "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                    "author": "packagecontrol-test",
                    "readme": "https://gitlab.com/packagecontrol-test/"
                              "package_control-tester/-/raw/master/readme.md",
                    "issues": None,
                    "donate": None,
                    "buy": None,
                    "sources": ["https://gitlab.com/packagecontrol-test"],
                    "labels": [],
                    "previous_names": [],
                    "releases": [{
                        "sublime_text": "*",
                        "date": "2020-07-15 10:50:38",
                        "version": "2020.07.15.10.50.38",
                        "platforms": ["*"],
                        "url": "https://gitlab.com/packagecontrol-test/"
                        "package_control-tester/-/archive/master/package_control-tester-master.zip"
                    }],
                    "last_modified": "2020-07-15 10:50:38"
                }
            )],
            list(provider.get_packages())
        )

    def test_get_broken_packages(self):
        provider = GitLabUserProvider("https://gitlab.com/packagecontrol-test", self.settings())
        self.assertEqual([], list(provider.get_broken_packages()))

    def test_get_renamed_packages(self):
        provider = GitLabUserProvider("https://gitlab.com/packagecontrol-test", self.settings())
        self.assertEqual({}, provider.get_renamed_packages())

    def test_get_sources(self):
        provider = GitLabUserProvider("https://gitlab.com/packagecontrol-test", self.settings())
        self.assertEqual(["https://gitlab.com/packagecontrol-test"], provider.get_sources())


@data_decorator
class JsonRepositoryProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self, extra=None):
        if not GH_PASS:
            self.skipTest("GitHub personal access token for %s not set via env var GH_PASS" % GH_USER)
        if not GL_PASS:
            self.skipTest("GitLab personal access token for %s not set via env var GL_PASS" % GL_USER)
        if not BB_PASS:
            self.skipTest("BitBucket app password for %s not set via env var BB_PASS" % BB_USER)

        settings = {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "api.github.com": [GH_USER, GH_PASS],
                "raw.githubusercontent.com": [GH_USER, GH_PASS],
                "gitlab.com": [GL_USER, GL_PASS],
                "api.bitbucket.org": [BB_USER, BB_PASS],
            }
        }
        if extra:
            settings.update(extra)

        return settings

    @data(
        (
            (
                # test_case name
                "10",
                # extra settings
                None,
                # repository url
                TEST_REPOSITORY_URL + "repository-1.0.json",
                # expected result
                []  # libraries not supported
            ),
            (
                "12",
                None,
                TEST_REPOSITORY_URL + "repository-1.2.json",
                []  # libraries not supported
            ),
            (
                "20_explicit",
                None,
                TEST_REPOSITORY_URL + "repository-2.0-explicit.json",
                []  # libraries not supported
            ),
            (
                "300_explicit",
                None,
                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json",
                [
                    (
                        "bz2",
                        {
                            "name": "bz2",
                            "author": "wbond",
                            "description": "Python bz2 module",
                            "issues": "https://github.com/wbond/package_control/issues",
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json"
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
                        "ssl-linux",
                        {
                            "name": "ssl-linux",
                            "description": "Python _ssl module for Linux",
                            "author": "wbond",
                            "issues": "https://github.com/wbond/package_control/issues",
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json"
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
                        "ssl-windows",
                        {
                            "name": "ssl-windows",
                            "description": "Python _ssl module for Sublime Text 2 on Windows",
                            "author": "wbond",
                            "issues": "https://github.com/wbond/package_control/issues",
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json"
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
                ]
            ),
            (
                "400_explicit",
                None,
                TEST_REPOSITORY_URL + "repository-4.0.0-explicit.json",
                [
                    (
                        "bz2",
                        {
                            "name": "bz2",
                            "author": "wbond",
                            "description": "Python bz2 module",
                            "issues": "https://github.com/wbond/package_control/issues",
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-explicit.json"
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
                        "ssl-linux",
                        {
                            "name": "ssl-linux",
                            "description": "Python _ssl module for Linux",
                            "author": "wbond",
                            "issues": "https://github.com/wbond/package_control/issues",
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-explicit.json"
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
                    (
                        "ssl-windows",
                        {
                            "name": "ssl-windows",
                            "description": "Python _ssl module for Sublime Text 2 on Windows",
                            "author": "wbond",
                            "issues": "https://github.com/wbond/package_control/issues",
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-explicit.json"
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
                ]
            ),
            (
                "400_pypi_releases",
                {"max_releases": 2},
                TEST_REPOSITORY_URL + "repository-4.0.0-pypi_releases.json",
                [
                    (
                        "coverage",
                        {
                            "name": "coverage",
                            "description": "The code coverage tool for Python",
                            "author": "Ned Batchelder",
                            "issues": "https://github.com/nedbat/coveragepy/issues",
                            "releases": [
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/9f/95/436887935a32fcead76c9f60b61f3fcd8940d4129bdbc50e2988e037a664"
                                           "/coverage-7.3.2-cp38-cp38-win_amd64.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:21:16",
                                    "sha256": "88ed2c30a49ea81ea3b7f172e0269c182a44c236eb394718f976239892c0a27a",
                                    "platforms": ["windows-x64"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/b1/6c/f3a0aaa1af42a950086713a1569e9992740babf822c606251f6e0c71f088"
                                           "/coverage-7.3.2-cp38-cp38-win32.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:21:14",
                                    "sha256": "307adb8bd3abe389a471e649038a71b4eb13bfd6b7dd9a129fa856f5c695cf92",
                                    "platforms": ["windows-x32"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/a0/a6/9deeff0c49d865cd1c5ae5efc9442ff234f9b0e9d15cb4a9cda58ec255cc"
                                           "/coverage-7.3.2-cp38-cp38-macosx_10_9_x86_64.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:20:57",
                                    "sha256": "f94b734214ea6a36fe16e96a70d941af80ff3bfd716c141300d95ebc85339738",
                                    "platforms": ["osx-x64"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/00/d8/5f69c3f146053edd13782355d004e57afce7824b7f8820fcb764e6ae8fac"
                                           "/coverage-7.3.2-cp38-cp38-macosx_11_0_arm64.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:20:59",
                                    "sha256": "af3d828d2c1cbae52d34bdbb22fcd94d1ce715d95f1a012354a75e5913f1bda2",
                                    "platforms": ["osx-arm64"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/8d/1a/e4d0775502fae6ce2c2dd3692a66aff3b18e89757567e35680b9c63d89c5"
                                           "/coverage-7.3.2-cp38-cp38-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:21:06",
                                    "sha256": "d8f17966e861ff97305e0801134e69db33b143bbfb36436efb9cfff6ec7b2fd9",
                                    "platforms": ["linux-x64"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/48/c1/b6c03b1a0aa07dd145d650b6e5107dab59a2e0c99b31184f37d49b3fd840"
                                           "/coverage-7.3.2-cp38-cp38-manylinux_2_5_i686.manylinux1_i686.manylinux_2_17_i686.manylinux2014_i686.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:21:04",
                                    "sha256": "c9eacf273e885b02a0273bb3a2170f30e2d53a6d53b72dbe02d6701b5296101c",
                                    "platforms": ["linux-x32"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/ab/82/9d5243dc4795d736b31f8e05e33c13741244e1e9bfbde7b3908141e27036"
                                           "/coverage-7.3.2-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
                                    "version": "7.3.2",
                                    "date": "2023-10-02 18:21:02",
                                    "sha256": "630b13e3036e13c7adc480ca42fa7afc2a5d938081d28e20903cf7fd687872e2",
                                    "platforms": ["linux-arm64"],
                                    "python_versions": ["3.8"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/3b/2f/c641609b79e292a4a29375c4af0cf8156c36a0613000513b05eb1a838a59"
                                           "/coverage-4.5.4-cp33-cp33m-macosx_10_10_x86_64.whl",
                                    "version": "4.5.4",
                                    "date": "2019-07-29 15:29:28",
                                    "sha256": "6b62544bb68106e3f00b21c8930e83e584fdca005d4fffd29bb39fb3ffa03cb5",
                                    "platforms": ["osx-x64"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/15/0d/468dc25311a5f7cb08b6364f1da8ac27e69e145b1eaf95d47a98141b895c"
                                           "/coverage-4.5.3-cp33-cp33m-macosx_10_10_x86_64.whl",
                                    "version": "4.5.3",
                                    "date": "2019-03-10 15:16:49",
                                    "sha256": "c968a6aa7e0b56ecbd28531ddf439c2ec103610d3e2bf3b75b813304f8cb7723",
                                    "platforms": ["osx-x64"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/ce/e5/7d0c5440de5ba0075b304478d6309b16cb4681063050b192d8d9398aa7f0"
                                           "/coverage-4.5.1-cp33-cp33m-manylinux1_x86_64.whl",
                                    "version": "4.5.1",
                                    "date": "2018-02-10 20:39:36",
                                    "sha256": "5a13ea7911ff5e1796b6d5e4fbbf6952381a611209b736d48e675c2756f3f74e",
                                    "platforms": ["linux-x64"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/fa/fb/f058805db61a6ac8cce5121c5a8a1841239af1b69fac59cbd8d7bfbf8015"
                                           "/coverage-4.5.1-cp33-cp33m-manylinux1_i686.whl",
                                    "version": "4.5.1",
                                    "date": "2018-02-10 20:39:35",
                                    "sha256": "701cd6093d63e6b8ad7009d8a92425428bc4d6e7ab8d75efbb665c806c1d79ba",
                                    "platforms": ["linux-x32"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/0b/4e/2085ca2269788daf683f7561ad37f09c325e70d0fe85aa2ada3fcd8c0c6b"
                                           "/coverage-4.5-cp33-cp33m-manylinux1_x86_64.whl",
                                    "version": "4.5",
                                    "date": "2018-02-03 22:16:13",
                                    "sha256": "0f2315c793b1360f80a9119fff76efb7b4e5ab5062651dff515e681719f29689",
                                    "platforms": ["linux-x64"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/a7/2d/d20247c1aae6829c64f1ffd3353424228b412eab6157fa622437a396d011"
                                           "/coverage-4.5-cp33-cp33m-manylinux1_i686.whl",
                                    "version": "4.5",
                                    "date": "2018-02-03 22:16:10",
                                    "sha256": "2890cb40464686c0c1dccc1223664bbc34d85af053bc5dbcd71ea13959e264f2",
                                    "platforms": ["linux-x32"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/b1/55/02815cb8abb091033abb979ebde5122bb33b85c5987dede9ccd019033d19"
                                           "/coverage-4.2-cp33-cp33m-win_amd64.whl",
                                    "version": "4.2",
                                    "date": "2016-07-26 21:09:17",
                                    "sha256": "bd4eba631f07cae8cdb9c55c144f165649e6701b962f9d604b4e00cf8802406c",
                                    "platforms": ["windows-x64"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/a0/34/1185348cc5c541bbdf107438f0f0ea9df5d9a4233a974e9228b6ee815489"
                                           "/coverage-4.2-cp33-cp33m-win32.whl",
                                    "version": "4.2",
                                    "date": "2016-07-26 21:09:13",
                                    "sha256": "38e87c46d364b8b3ac4d161586707345b7bc7b16855be1751345fc91be702ff7",
                                    "platforms": ["windows-x32"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/0c/a1/8c4580eee7f09dcf0bac9ceeca7db1abaca856333fae24aac8f54f94b1c9"
                                           "/coverage-4.1-cp33-cp33m-win_amd64.whl",
                                    "version": "4.1",
                                    "date": "2016-05-21 15:13:24",
                                    "sha256": "a4eb2ca4ecf2c1ec02492302c8755d182ae81f81e392f8a513be13f212af0b14",
                                    "platforms": ["windows-x64"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                },
                                {
                                    "url": "https://files.pythonhosted.org/packages"
                                           "/b6/ce/8bb7745039931ef0412bd903af6584f47ece266f39364d550a18f0f60fca"
                                           "/coverage-4.1-cp33-cp33m-win32.whl",
                                    "version": "4.1",
                                    "date": "2016-05-21 15:13:17",
                                    "sha256": "a6a092bf2ab7d5dbce2a249e6aa23ea2e2181dc89f575cc9b17341a89e479312",
                                    "platforms": ["windows-x32"],
                                    "python_versions": ["3.3"],
                                    "sublime_text": "*"
                                }
                            ],
                            "sources": [TEST_REPOSITORY_URL + "repository-4.0.0-pypi_releases.json"]
                        }
                    )
                ]
            )
        ),
        first_param_name_suffix=True
    )
    def get_libraries(self, extra_settings, url, result):
        provider = JsonRepositoryProvider(url, self.settings(extra_settings))
        self.assertEqual(result, list(provider.get_libraries()))

    @data(
        (
            (
                # test_case name
                "10",
                # repository url
                TEST_REPOSITORY_URL + "repository-1.0.json",
                # expected result
                []  # no longer supported by PC4.0+, empty results
            ),
            (
                "12",
                TEST_REPOSITORY_URL + "repository-1.2.json",
                []  # no longer supported by PC4.0+, empty results
            ),
            (
                "20_explicit",
                TEST_REPOSITORY_URL + "repository-2.0-explicit.json",
                [(
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
                        "sources": [
                            TEST_REPOSITORY_URL + "repository-2.0-explicit.json"
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
                )]
            ),
            (
                "20_github_details",
                TEST_REPOSITORY_URL + "repository-2.0-github_details.json",
                [(
                    "package_control-tester-2.0-gh",
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
                            TEST_REPOSITORY_URL + "repository-2.0-github_details.json",
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
                )]
            ),
            (
                "20_bitbucket_details",
                TEST_REPOSITORY_URL + "repository-2.0-bitbucket_details.json",
                [(
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
                        "sources": [
                            TEST_REPOSITORY_URL + "repository-2.0-bitbucket_details.json",
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
                )]
            ),
            (
                "300_explicit",
                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json",
                [(
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
                        "sources": [
                            TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json"
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
                )]
            ),
            (
                "300_github",
                TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
                [
                    (
                        "package_control-tester-3.0.0-gh-tags",
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
                                TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
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
                        "package_control-tester-3.0.0-gh-tags_base",
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
                                TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json"
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
                        "package_control-tester-3.0.0-gh-tags_prefix",
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
                                TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
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
                        "package_control-tester-3.0.0-gh-branch",
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
                                TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
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
                ]
            ),
            (
                "300_gitlab",
                TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
                [
                    (
                        "package_control-tester-3.0.0-gl-tags",
                        {
                            "name": "package_control-tester-3.0.0-gl-tags",
                            "author": "packagecontrol-test",
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "readme": "https://gitlab.com/packagecontrol-test/"
                                      "package_control-tester/-/raw/master/readme.md",
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
                                "https://gitlab.com/packagecontrol-test/package_control-tester"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "version": "1.0.1",
                                    "date": "2020-07-15 10:50:38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip",
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
                            "readme": None,
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "version": "1.0.1",
                                    "date": "2020-07-15 10:50:38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip",
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
                            "author": "packagecontrol-test",
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "readme": "https://gitlab.com/packagecontrol-test/"
                                      "package_control-tester/-/raw/master/readme.md",
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
                                "https://gitlab.com/packagecontrol-test/package_control-tester"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "version": "1.0.1",
                                    "date": "2020-07-15 10:50:38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/win-1.0.1/"
                                           "package_control-tester-win-1.0.1.zip",
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
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "author": "packagecontrol-test",
                            "readme": "https://gitlab.com/packagecontrol-test/"
                                      "package_control-tester/-/raw/master/readme.md",
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
                                "https://gitlab.com/packagecontrol-test/package_control-tester"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "date": "2020-07-15 10:50:38",
                                    "version": "2020.07.15.10.50.38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/master/"
                                           "package_control-tester-master.zip",
                                    "sublime_text": "*",
                                    "platforms": ["*"]
                                }
                            ]
                        }
                    )
                ]
            ),
            (
                "300_bitbucket",
                TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json",
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
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json",
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
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json",
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
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json",
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
                ]
            ),
            (
                "400_explicit",
                TEST_REPOSITORY_URL + "repository-4.0.0-explicit.json",
                [(
                    "package_control-tester-4.0.0",
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
                            TEST_REPOSITORY_URL + "repository-4.0.0-explicit.json"
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
                )]
            ),
            (
                "400_github",
                TEST_REPOSITORY_URL + "repository-4.0.0-github_releases.json",
                [
                    (
                        "package_control-tester-4.0.0-gh-tags",
                        {
                            "name": "package_control-tester-4.0.0-gh-tags",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-github_releases.json",
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
                        "package_control-tester-4.0.0-gh-tags_base",
                        {
                            "name": "package_control-tester-4.0.0-gh-tags_base",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-github_releases.json"
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
                        "package_control-tester-4.0.0-gh-tags_prefix",
                        {
                            "name": "package_control-tester-4.0.0-gh-tags_prefix",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-github_releases.json",
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
                        "package_control-tester-4.0.0-gh-branch",
                        {
                            "name": "package_control-tester-4.0.0-gh-branch",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-github_releases.json",
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
                ]
            ),
            (
                "400_gitlab",
                TEST_REPOSITORY_URL + "repository-4.0.0-gitlab_releases.json",
                [
                    (
                        "package_control-tester-4.0.0-gl-tags",
                        {
                            "name": "package_control-tester-4.0.0-gl-tags",
                            "author": "packagecontrol-test",
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "readme": "https://gitlab.com/packagecontrol-test/"
                                      "package_control-tester/-/raw/master/readme.md",
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-gitlab_releases.json",
                                "https://gitlab.com/packagecontrol-test/package_control-tester"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "version": "1.0.1",
                                    "date": "2020-07-15 10:50:38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip",
                                    "sublime_text": "*",
                                    "platforms": ["*"]
                                }
                            ]
                        }
                    ),
                    (
                        "package_control-tester-4.0.0-gl-tags_base",
                        {
                            "name": "package_control-tester-4.0.0-gl-tags_base",
                            "author": "packagecontrol",
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "readme": None,
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-gitlab_releases.json"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "version": "1.0.1",
                                    "date": "2020-07-15 10:50:38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/1.0.1/package_control-tester-1.0.1.zip",
                                    "sublime_text": "*",
                                    "platforms": ["*"]
                                }
                            ]
                        }
                    ),
                    (
                        "package_control-tester-4.0.0-gl-tags_prefix",
                        {
                            "name": "package_control-tester-4.0.0-gl-tags_prefix",
                            "author": "packagecontrol-test",
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "readme": "https://gitlab.com/packagecontrol-test/"
                                      "package_control-tester/-/raw/master/readme.md",
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-gitlab_releases.json",
                                "https://gitlab.com/packagecontrol-test/package_control-tester"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "version": "1.0.1",
                                    "date": "2020-07-15 10:50:38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/win-1.0.1/"
                                           "package_control-tester-win-1.0.1.zip",
                                    "sublime_text": "<3000",
                                    "platforms": ["windows"]
                                }
                            ]
                        }
                    ),
                    (
                        "package_control-tester-4.0.0-gl-branch",
                        {
                            "name": "package_control-tester-4.0.0-gl-branch",
                            "description": "A test of Package Control upgrade messages with "
                                           "explicit versions, but date-based releases.",
                            "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                            "author": "packagecontrol-test",
                            "readme": "https://gitlab.com/packagecontrol-test/"
                                      "package_control-tester/-/raw/master/readme.md",
                            "issues": None,
                            "donate": None,
                            "buy": None,
                            "sources": [
                                TEST_REPOSITORY_URL + "repository-4.0.0-gitlab_releases.json",
                                "https://gitlab.com/packagecontrol-test/package_control-tester"
                            ],
                            "labels": [],
                            "previous_names": [],
                            "last_modified": "2020-07-15 10:50:38",
                            "releases": [
                                {
                                    "date": "2020-07-15 10:50:38",
                                    "version": "2020.07.15.10.50.38",
                                    "url": "https://gitlab.com/packagecontrol-test/"
                                           "package_control-tester/-/archive/master/"
                                           "package_control-tester-master.zip",
                                    "sublime_text": "*",
                                    "platforms": ["*"]
                                }
                            ]
                        }
                    )
                ]
            ),
            (
                "400_bitbucket",
                TEST_REPOSITORY_URL + "repository-4.0.0-bitbucket_releases.json",
                [
                    (
                        "package_control-tester-4.0.0-bb-tags",
                        {
                            "name": "package_control-tester-4.0.0-bb-tags",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-bitbucket_releases.json",
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
                        "package_control-tester-4.0.0-bb-tags_prefix",
                        {
                            "name": "package_control-tester-4.0.0-bb-tags_prefix",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-bitbucket_releases.json",
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
                        "package_control-tester-4.0.0-bb-branch",
                        {
                            "name": "package_control-tester-4.0.0-bb-branch",
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
                                TEST_REPOSITORY_URL + "repository-4.0.0-bitbucket_releases.json",
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
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def get_packages(self, url, result):
        provider = JsonRepositoryProvider(url, self.settings())
        self.assertEqual(result, list(provider.get_packages()))


class ChannelProviderTests(unittest.TestCase):
    maxDiff = None

    def settings(self):
        return {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "raw.githubusercontent.com": [GH_USER, GH_PASS],
            }
        }

    def test_get_packages_12(self):
        provider = ChannelProvider(TEST_REPOSITORY_URL + "channel-1.2.json", self.settings())
        self.assertRaises(
            InvalidChannelFileException,
            list,
            provider.get_packages(
                TEST_REPOSITORY_URL + "repository-1.2.json"
            )
        )

    def test_get_renamed_packages_12(self):
        provider = ChannelProvider(TEST_REPOSITORY_URL + "channel-1.2.json", self.settings())
        self.assertRaises(
            InvalidChannelFileException,
            provider.get_renamed_packages
        )

    def test_get_repositories_12(self):
        provider = ChannelProvider(TEST_REPOSITORY_URL + "channel-1.2.json", self.settings())
        self.assertRaises(
            InvalidChannelFileException,
            provider.get_repositories
        )

    def test_get_sources_12(self):
        provider = ChannelProvider(TEST_REPOSITORY_URL + "channel-1.2.json", self.settings())
        self.assertRaises(
            InvalidChannelFileException,
            provider.get_sources
        )

    @data(
        (
            (
                "300_repository_300_explicit",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json",
                [
                    (
                        "bz2",
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
                        "ssl-linux",
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
                        "ssl-windows",
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
                ]
            )
        ),
        first_param_name_suffix=True
    )
    def get_libraries(self, url, repo_url, result):
        self.maxDiff = None
        provider = ChannelProvider(url, self.settings())
        self.assertEqual(result, list(provider.get_libraries(repo_url)))

    @data(
        (
            (
                "20_repository_10_explicit",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                TEST_REPOSITORY_URL + "repository-1.0.json",
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
                ]
            ),
            (
                "20_repository_12_explicit",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                TEST_REPOSITORY_URL + "repository-1.2.json",
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
                ]
            ),
            (
                "20_repository_20_explicit",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                TEST_REPOSITORY_URL + "repository-2.0-explicit.json",
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
                ]
            ),
            (
                "20_bitbucket_details",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                TEST_REPOSITORY_URL + "repository-2.0-bitbucket_details.json",
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
                ]
            ),
            (
                "20_github_details",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                TEST_REPOSITORY_URL + "repository-2.0-github_details.json",
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
                ]
            ),
            (
                "300_repository_300_explicit",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json",
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
                ]
            ),
            (
                "300_bitbucket_tags",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json",
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
                ]
            ),
            (
                "300_github_tags",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
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
                ]
            ),
            (
                "300_gitlab_tags",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
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
                            "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md",
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
                            "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md",
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
                            "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md",
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
                            "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md",
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
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def get_packages(self, url, repo_url, result):
        self.maxDiff = None
        provider = ChannelProvider(url, self.settings())
        self.assertEqual(result, list(provider.get_packages(repo_url)))

    @data(
        (
            (
                "20",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                {}
            ),
            (
                "300",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                {}
            )
        ),
        first_param_name_suffix=True
    )
    def get_renamed_packages(self, url, result):
        provider = ChannelProvider(url, self.settings())
        self.assertEqual(result, provider.get_renamed_packages())

    @data(
        (
            (
                "20",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                [
                    TEST_REPOSITORY_URL + "repository-1.0.json",
                    TEST_REPOSITORY_URL + "repository-1.2.json",
                    TEST_REPOSITORY_URL + "repository-2.0-explicit.json",
                    TEST_REPOSITORY_URL + "repository-2.0-github_details.json",
                    TEST_REPOSITORY_URL + "repository-2.0-bitbucket_details.json"
                ]
            ),
            (
                "300",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                [
                    TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json",
                    TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
                    TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
                    TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json"
                ]
            )
        ),
        first_param_name_suffix=True
    )
    def get_repositories(self, url, result):
        provider = ChannelProvider(url, self.settings())
        self.assertEqual(result, provider.get_repositories())

    @data(
        (
            (
                "20",
                TEST_REPOSITORY_URL + "channel-2.0.json",
                [
                    TEST_REPOSITORY_URL + "repository-1.0.json",
                    TEST_REPOSITORY_URL + "repository-1.2.json",
                    TEST_REPOSITORY_URL + "repository-2.0-explicit.json",
                    TEST_REPOSITORY_URL + "repository-2.0-github_details.json",
                    TEST_REPOSITORY_URL + "repository-2.0-bitbucket_details.json"
                ]
            ),
            (
                "300",
                TEST_REPOSITORY_URL + "channel-3.0.0.json",
                [
                    TEST_REPOSITORY_URL + "repository-3.0.0-explicit.json",
                    TEST_REPOSITORY_URL + "repository-3.0.0-github_releases.json",
                    TEST_REPOSITORY_URL + "repository-3.0.0-gitlab_releases.json",
                    TEST_REPOSITORY_URL + "repository-3.0.0-bitbucket_releases.json"
                ]
            )
        ),
        first_param_name_suffix=True
    )
    def get_sources(self, url, result):
        provider = ChannelProvider(url, self.settings())
        self.assertEqual(result, provider.get_sources())
