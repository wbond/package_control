import unittest

from ..clients.bitbucket_client import BitBucketClient
from ..clients.github_client import GitHubClient
from ..clients.gitlab_client import GitLabClient
from ..clients.pypi_client import PyPiClient
from ..clients.readme_client import ReadmeClient
from ..http_cache import HttpCache
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


@data_decorator
class BitBucketClientTests(unittest.TestCase):
    maxDiff = None

    def settings(self, extra=None):
        if not BB_PASS:
            self.skipTest("BitBucket app password for %s not set via env var BB_PASS" % BB_USER)

        settings = {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "api.bitbucket.org": [BB_USER, BB_PASS]
            }
        }
        if extra:
            settings.update(extra)

        return settings

    @data(
        (
            (
                "1",
                "https://bitbucket.org",
                (None, None, None)
            ),
            (
                "2",
                "https://bitbucket.org/",
                (None, None, None)
            ),
            (
                "3",
                "https://bitbucket.org/packagecontrol-test",
                ("packagecontrol-test", None, None)
            ),
            (
                "4",
                "https://bitbucket.org/packagecontrol-test/",
                ("packagecontrol-test", None, None)
            ),
            (
                "5",
                "https://bitbucket.org/packagecontrol-test/package_control-tester",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "6",
                "https://bitbucket.org/packagecontrol-test/package_control-tester/",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "7",
                "https://bitbucket.org/packagecontrol-test/package_control-tester.git",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "8",
                "https://bitbucket.org/packagecontrol-test/package_control-tester/src/master",
                ("packagecontrol-test", "package_control-tester", "master")
            ),
            (
                "9",
                "https://bitbucket.org/packagecontrol-test/package_control-tester/src/master/",
                ("packagecontrol-test", "package_control-tester", "master")
            ),
            (
                "10",
                "https://bitbucket.org/packagecontrol-test/package_control-tester/src/foo/bar",
                ("packagecontrol-test", "package_control-tester", "foo/bar")
            ),
            (
                "11",
                "https://bitbucket.org/packagecontrol-test/package_control-tester/src/foo/bar/",
                ("packagecontrol-test", "package_control-tester", "foo/bar")
            ),
            (
                "12",
                "https://bitbucket.org/packagecontrol-test/package_control-tester#tags",
                (None, None, None)
            ),
            (
                "13",
                "https://bitbucket.org/packagecontrol-test/package_control-tester/#tags",
                (None, None, None)
            ),
            (
                "14",
                "https://bitbucket;org/packagecontrol-test/package_control-tester",
                (None, None, None)
            ),
        ),
        first_param_name_suffix=True
    )
    def repo_user_branch(self, url, result):
        client = BitBucketClient(self.settings())
        self.assertEqual(result, client.user_repo_branch(url))

    def test_repo_info(self):
        client = BitBucketClient(self.settings())
        self.assertEqual(
            {
                "name": "package_control-tester",
                "description": "A test of Package Control upgrade messages with "
                               "explicit versions, but date-based releases.",
                "homepage": "https://bitbucket.org/wbond/package_control-tester",
                "author": "wbond",
                "readme": "https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md",
                "issues": "https://bitbucket.org/wbond/package_control-tester/issues",
                "donate": None,
                "default_branch": "master"
            },
            client.repo_info("https://bitbucket.org/wbond/package_control-tester")
        )

    def test_user_info(self):
        client = BitBucketClient(self.settings())
        self.assertEqual(None, client.user_info("https://bitbucket.org/wbond"))

    def test_readme(self):
        client = ReadmeClient(self.settings())
        self.assertEqual(
            {
                "filename": "readme.md",
                "contents": "# Package Control Tester\n\nThis repo is used to test the various "
                            "clients and providers that are part of\nPackage Control.\n",
                "format": "markdown"
            },
            client.readme_info("https://bitbucket.org/wbond/package_control-tester/raw/master/readme.md")
        )

    @data(
        (
            (
                "branch_downloads",  # name
                None,  # extra_settings
                "https://bitbucket.org/wbond/package_control-tester",  # url
                None,  # tag-prefix
                [
                    {
                        "date": LAST_COMMIT_TIMESTAMP,
                        "version": LAST_COMMIT_VERSION,
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/master.zip"
                    }
                ]
            ),
            (
                "tags_downloads",
                None,
                "https://bitbucket.org/wbond/package_control-tester#tags",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip"
                    },
                    {
                        "date": "2014-11-12 15:14:23",
                        "version": "1.0.1-beta",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip"
                    },
                    {
                        "date": "2014-11-12 15:14:13",
                        "version": "1.0.0",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip"
                    },
                    {
                        "date": "2014-11-12 02:02:22",
                        "version": "0.9.0",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip"
                    }
                ]
            ),
            (
                "tags_limited_downloads",
                {"max_releases": 1},
                "https://bitbucket.org/wbond/package_control-tester#tags",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip"
                    }
                ]
            ),
            (
                "tags_with_prefix_downloads",
                None,
                "https://bitbucket.org/wbond/package_control-tester#tags",
                "win-",
                [
                    {
                        "date": "2014-11-28 20:54:15",
                        "version": "1.0.2",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/win-1.0.2.zip"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info(self, extra_settings, url, tag_prefix, result):
        client = BitBucketClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info(url, tag_prefix))

    @data(
        (
            (
                "via_repo_url",  # name
                None,  # extra_settings
                "https://bitbucket.org/wbond/package_control-tester",  # url
                None,  # tag-prefix
                [
                    {
                        "date": LAST_COMMIT_TIMESTAMP,
                        "version": LAST_COMMIT_VERSION,
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/master.zip"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_branch(self, extra_settings, url, branch, result):
        client = BitBucketClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info_from_branch(url, branch))

    @data(
        (
            (
                "via_repo_url",
                None,
                "https://bitbucket.org/wbond/package_control-tester",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip"
                    },
                    {
                        "date": "2014-11-12 15:14:23",
                        "version": "1.0.1-beta",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1-beta.zip"
                    },
                    {
                        "date": "2014-11-12 15:14:13",
                        "version": "1.0.0",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.0.zip"
                    },
                    {
                        "date": "2014-11-12 02:02:22",
                        "version": "0.9.0",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/0.9.0.zip"
                    }
                ]
            ),
            (
                "via_repo_url_limited",
                {"max_releases": 1},
                "https://bitbucket.org/wbond/package_control-tester",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/1.0.1.zip"
                    }
                ]
            ),
            (
                "via_repo_url_with_prefix",
                None,
                "https://bitbucket.org/wbond/package_control-tester",
                "win-",
                [
                    {
                        "date": "2014-11-28 20:54:15",
                        "version": "1.0.2",
                        "url": "https://bitbucket.org/wbond/package_control-tester/get/win-1.0.2.zip"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_tags(self, extra_settings, url, tag_prefix, result):
        client = BitBucketClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info_from_tags(url, tag_prefix))

    @data(
        (
            (
                # url
                "https://bitbucket.org/wbond/package_control-tester",
                # asset_templates
                [
                    # asset name pattern, { selectors }
                    ("package_control-tester.sublime-package", {}),
                ],
                # tag prefix
                None,
                # results (note: not supported by BitBucket Client)
                None,
            ),
        )
    )
    def download_info_from_releases(self, url, asset_templates, tag_prefix, result):
        client = BitBucketClient(self.settings())
        self.assertEqual(result, client.download_info_from_releases(url, asset_templates, tag_prefix))


@data_decorator
class GitHubClientTests(unittest.TestCase):
    maxDiff = None

    def settings(self, extra=None):
        if not GH_PASS:
            self.skipTest("GitHub personal access token for %s not set via env var GH_PASS" % GH_USER)

        settings = {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "api.github.com": [GH_USER, GH_PASS],
                "raw.githubusercontent.com": [GH_USER, GH_PASS],
            }
        }
        if extra:
            settings.update(extra)

        return settings

    @data(
        (
            (
                "1",
                "https://github.com",
                (None, None, None)
            ),
            (
                "2",
                "https://github.com/",
                (None, None, None)
            ),
            (
                "3",
                "https://github.com/packagecontrol-test",
                ("packagecontrol-test", None, None)
            ),
            (
                "4",
                "https://github.com/packagecontrol-test/",
                ("packagecontrol-test", None, None)
            ),
            (
                "5",
                "https://github.com/packagecontrol-test/package_control-tester",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "6",
                "https://github.com/packagecontrol-test/package_control-tester/",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "7",
                "https://github.com/packagecontrol-test/package_control-tester.git",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "8",
                "https://github.com/packagecontrol-test/package_control-tester/tree/master",
                ("packagecontrol-test", "package_control-tester", "master")
            ),
            (
                "9",
                "https://github.com/packagecontrol-test/package_control-tester/tree/master/",
                ("packagecontrol-test", "package_control-tester", "master")
            ),
            (
                "10",
                "https://github.com/packagecontrol-test/package_control-tester/tree/foo/bar",
                ("packagecontrol-test", "package_control-tester", "foo/bar")
            ),
            (
                "11",
                "https://github.com/packagecontrol-test/package_control-tester/tree/foo/bar/",
                ("packagecontrol-test", "package_control-tester", "foo/bar")
            ),
            (
                "12",
                "https://github.com/packagecontrol-test/package_control-tester/tags",
                (None, None, None)
            ),
            (
                "13",
                "https://github.com/packagecontrol-test/package_control-tester/tags/",
                (None, None, None)
            ),
            (
                "14",
                "https://github;com/packagecontrol-test/package_control-tester",
                (None, None, None)
            ),
        ),
        first_param_name_suffix=True
    )
    def repo_user_branch(self, url, result):
        client = GitHubClient(self.settings())
        self.assertEqual(result, client.user_repo_branch(url))

    def test_repo_info(self):
        client = GitHubClient(self.settings())
        self.assertEqual(
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
                "default_branch": "master"
            },
            client.repo_info("https://github.com/packagecontrol-test/package_control-tester")
        )

    def test_user_info(self):
        client = GitHubClient(self.settings())
        self.assertEqual(
            [{
                "name": "package_control-tester",
                "description": "A test of Package Control upgrade messages with "
                               "explicit versions, but date-based releases.",
                "homepage": "https://github.com/packagecontrol-test/package_control-tester",
                "author": "packagecontrol-test",
                "readme": "https://raw.githubusercontent.com/packagecontrol-test"
                          "/package_control-tester/master/readme.md",
                "issues": "https://github.com/packagecontrol-test/package_control-tester/issues",
                "donate": None,
                "default_branch": "master"
            }],
            client.user_info("https://github.com/packagecontrol-test")
        )

    def test_readme(self):
        client = ReadmeClient(self.settings())
        self.assertEqual(
            {
                "filename": "readme.md",
                "contents": "# Package Control Tester\n\nThis repo is used to test the "
                            "various clients and providers that are part of\nPackage Control.\n",
                "format": "markdown"
            },
            client.readme_info(
                "https://raw.githubusercontent.com/packagecontrol-test/package_control-tester/master/readme.md"
            )
        )

    @data(
        (
            (
                "branch_downloads",  # name
                None,  # extra_settings
                "https://github.com/packagecontrol-test/package_control-tester",  # url
                None,  # tag-prefix
                [
                    {
                        "date": LAST_COMMIT_TIMESTAMP,
                        "version": LAST_COMMIT_VERSION,
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/master"
                    }
                ]
            ),
            (
                "tags_downloads",
                None,
                "https://github.com/packagecontrol-test/package_control-tester/tags",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.1"
                    },
                    {
                        "date": "2014-11-12 15:14:23",
                        "version": "1.0.1-beta",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.1-beta"
                    },
                    {
                        "date": "2014-11-12 15:14:13",
                        "version": "1.0.0",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.0"
                    },
                    {
                        "date": "2014-11-12 02:02:22",
                        "version": "0.9.0",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/0.9.0"
                    }
                ]
            ),
            (
                "limited_tags_downloads",
                {"max_releases": 1},
                "https://github.com/packagecontrol-test/package_control-tester/tags",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.1"
                    }
                ]
            ),
            (
                "tags_prefix_downloads",
                None,
                "https://github.com/packagecontrol-test/package_control-tester/tags",
                "win-",
                [
                    {
                        "date": "2014-11-28 20:54:15",
                        "version": "1.0.2",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/win-1.0.2"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info(self, extra_settings, url, tag_prefix, result):
        client = GitHubClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info(url, tag_prefix))

    @data(
        (
            (
                "via_repo_url",  # name
                None,  # extra_settings
                "https://github.com/packagecontrol-test/package_control-tester",  # url
                None,  # tag-prefix
                [
                    {
                        "date": LAST_COMMIT_TIMESTAMP,
                        "version": LAST_COMMIT_VERSION,
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/master"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_branch(self, extra_settings, url, branch, result):
        client = GitHubClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info_from_branch(url, branch))

    @data(
        (
            (
                "via_repo_url",
                None,
                "https://github.com/packagecontrol-test/package_control-tester",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.1"
                    },
                    {
                        "date": "2014-11-12 15:14:23",
                        "version": "1.0.1-beta",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.1-beta"
                    },
                    {
                        "date": "2014-11-12 15:14:13",
                        "version": "1.0.0",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.0"
                    },
                    {
                        "date": "2014-11-12 02:02:22",
                        "version": "0.9.0",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/0.9.0"
                    }
                ]
            ),
            (
                "via_repo_url_limited",
                {"max_releases": 1},
                "https://github.com/packagecontrol-test/package_control-tester",
                None,
                [
                    {
                        "date": "2014-11-12 15:52:35",
                        "version": "1.0.1",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/1.0.1"
                    }
                ]
            ),
            (
                "via_repo_url_with_prefix",
                None,
                "https://github.com/packagecontrol-test/package_control-tester",
                "win-",
                [
                    {
                        "date": "2014-11-28 20:54:15",
                        "version": "1.0.2",
                        "url": "https://codeload.github.com/"
                               "packagecontrol-test/package_control-tester/zip/win-1.0.2"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_tags(self, extra_settings, url, tag_prefix, result):
        client = GitHubClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info_from_tags(url, tag_prefix))

    @data(
        (
            (
                # url
                "https://github.com/packagecontrol-test/package_control-tester",
                # asset_templates
                [
                    # asset name pattern, { selectors }
                    ("package_control-tester.sublime-package", {}),
                ],
                # tag prefix
                None,
                # results (note: test repo"s don"t provide release assests to test against, unfortunatelly)
                [
                    # {
                    #     "date": "2014-11-12 15:52:35",
                    #     "version": "1.0.1",
                    #     "url": "https://github.com/packagecontrol-test/package_control-tester/"
                    #            "downloads/releases/1.0.1/package_control-tester.sublime-package"
                    # },
                    # {
                    #     "date": "2014-11-12 15:14:23",
                    #     "version": "1.0.1-beta",
                    #     "url": "https://github.com/packagecontrol-test/package_control-tester/"
                    #            "downloads/releases/1.0.1-beta/package_control-tester.sublime-package"
                    # },
                    # {
                    #     "date": "2014-11-12 15:14:13",
                    #     "version": "1.0.0",
                    #     "url": "https://github.com/packagecontrol-test/package_control-tester/"
                    #            "downloads/releases/1.0.0/package_control-tester.sublime-package"
                    # },
                    # {
                    #     "date": "2014-11-12 02:02:22",
                    #     "version": "0.9.0",
                    #     "url": "https://github.com/packagecontrol-test/package_control-tester/"
                    #            "downloads/releases/0.9.0/package_control-tester.sublime-package"
                    # }
                ]
            ),
            (
                "https://github.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-st4???.sublime-package",
                        {"sublime_text": ">=4107"}
                    )
                ],
                None,
                []
            ),
            (
                "https://github.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-st${st_build}.sublime-package",
                        {"sublime_text": ">=4107"}
                    )
                ],
                None,
                []
            ),
            (
                "https://github.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-${platform}.sublime-package",
                        {"platforms": ["*"]}
                    )
                ],
                None,
                []
            ),
            (
                "https://github.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-${platform}.sublime-package",
                        {"platforms": ["windows-x64", "linux-x64"]}
                    )
                ],
                None,
                []
            ),
            (
                "https://github.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-win-amd64.sublime-package",
                        {"platforms": ["windows-x64"]}
                    ),
                    (
                        "package_control-tester-win-arm64.sublime-package",
                        {"platforms": ["windows-arm64"]}
                    ),
                    (
                        "package_control-tester-linux-aarch64.sublime-package",
                        {"platforms": ["linux-arm64"]}
                    )
                ],
                None,
                []
            ),
        )
    )
    def download_info_from_releases(self, url, asset_templates, tag_prefix, result):
        client = GitHubClient(self.settings())
        self.assertEqual(result, client.download_info_from_releases(url, asset_templates, tag_prefix))


@data_decorator
class GitLabClientTests(unittest.TestCase):
    maxDiff = None

    def settings(self, extra=None):
        if not GL_PASS:
            self.skipTest("GitLab personal access token for %s not set via env var GL_PASS" % GL_USER)

        settings = {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT,
            "http_basic_auth": {
                "gitlab.com": [GL_USER, GL_PASS]
            }
        }
        if extra:
            settings.update(extra)

        return settings

    @data(
        (
            (
                "1",
                "https://gitlab.com",
                (None, None, None)
            ),
            (
                "2",
                "https://gitlab.com/",
                (None, None, None)
            ),
            (
                "3",
                "https://gitlab.com/packagecontrol-test",
                ("packagecontrol-test", None, None)
            ),
            (
                "4",
                "https://gitlab.com/packagecontrol-test/",
                ("packagecontrol-test", None, None)
            ),
            (
                "5",
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "6",
                "https://gitlab.com/packagecontrol-test/package_control-tester/",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "7",
                "https://gitlab.com/packagecontrol-test/package_control-tester.git",
                ("packagecontrol-test", "package_control-tester", None)
            ),
            (
                "8",
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master",
                ("packagecontrol-test", "package_control-tester", "master")
            ),
            (
                "9",
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/master/",
                ("packagecontrol-test", "package_control-tester", "master")
            ),
            (
                "10",
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/foo/bar",
                ("packagecontrol-test", "package_control-tester", "foo/bar")
            ),
            (
                "11",
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tree/foo/bar/",
                ("packagecontrol-test", "package_control-tester", "foo/bar")
            ),
            (
                "12",
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tags",
                (None, None, None)
            ),
            (
                "13",
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tags/",
                (None, None, None)
            ),
            (
                "14",
                "https://gitlab;com/packagecontrol-test/package_control-tester",
                (None, None, None)
            ),
        ),
        first_param_name_suffix=True
    )
    def repo_user_branch(self, url, result):
        client = GitLabClient(self.settings())
        self.assertEqual(result, client.user_repo_branch(url))

    def test_repo_info(self):
        client = GitLabClient(self.settings())
        self.assertEqual(
            {
                "name": "package_control-tester",
                "description":
                    "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                "readme":
                    "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md",
                "author": "packagecontrol-test",
                "issues": None,
                "donate": None,
                "default_branch": "master"
            },
            client.repo_info(
                "https://gitlab.com/packagecontrol-test/package_control-tester"
            )
        )

    def test_user_info(self):
        client = GitLabClient(self.settings())
        self.assertEqual(
            [
                {
                    "name": "package_control-tester",
                    "description":
                        "A test of Package Control upgrade messages with explicit versions, but date-based releases.",
                    "homepage": "https://gitlab.com/packagecontrol-test/package_control-tester",
                    "readme": "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md",
                    "author": "packagecontrol-test",
                    "issues": None,
                    "donate": None,
                    "default_branch": "master"
                }
            ],
            client.user_info(
                "https://gitlab.com/packagecontrol-test"
            )
        )

    def test_readme(self):
        client = ReadmeClient(self.settings())
        self.assertEqual(
            {
                "filename": "readme.md",
                "contents":
                    "# Package Control Tester\n\nThis repo is used to test the "
                    "various clients and providers that are part of\nPackage Control.\n",
                "format": "markdown"
            },
            client.readme_info(
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/raw/master/readme.md"
            )
        )

    @data(
        (
            (
                "branch_downloads",  # name
                None,  # extra_settings
                "https://gitlab.com/packagecontrol-test/package_control-tester",  # url
                None,  # tag-prefix
                [
                    {
                        "date": "2020-07-15 10:50:38",
                        "version": "2020.07.15.10.50.38",
                        "url":
                            "https://gitlab.com/packagecontrol-test/package_control-tester"
                            "/-/archive/master/package_control-tester-master.zip"
                    }
                ]
            ),
            (
                "tags_downloads",
                None,
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tags",
                None,
                [
                    {
                        "date": "2020-07-15 10:50:38",
                        "version": "1.0.1",
                        "url":
                            "https://gitlab.com/packagecontrol-test/package_control-tester"
                            "/-/archive/1.0.1/package_control-tester-1.0.1.zip"
                    }
                ]
            ),
            (
                "tags_with_prefix_downloads",
                None,
                "https://gitlab.com/packagecontrol-test/package_control-tester/-/tags",
                "win-",
                [
                    {
                        "date": "2020-07-15 10:50:38",
                        "version": "1.0.1",
                        "url":
                            "https://gitlab.com/packagecontrol-test/package_control-tester"
                            "/-/archive/win-1.0.1/package_control-tester-win-1.0.1.zip"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info(self, extra_settings, url, tag_prefix, result):
        client = GitLabClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info(url, tag_prefix))

    @data(
        (
            (
                "via_repo_url",
                None,
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                None,
                [
                    {
                        "date": "2020-07-15 10:50:38",
                        "version": "2020.07.15.10.50.38",
                        "url":
                            "https://gitlab.com/packagecontrol-test/package_control-tester"
                            "/-/archive/master/package_control-tester-master.zip"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_branch(self, extra_settings, url, branch, result):
        client = GitLabClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info_from_branch(url, branch))

    @data(
        (
            (
                "via_repo_url",
                None,
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                None,
                [
                    {
                        "date": "2020-07-15 10:50:38",
                        "version": "1.0.1",
                        "url":
                            "https://gitlab.com/packagecontrol-test/package_control-tester"
                            "/-/archive/1.0.1/package_control-tester-1.0.1.zip"
                    }
                ]
            ),
            (
                "via_repo_url_with_prefix",
                None,
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                "win-",
                [
                    {
                        "date": "2020-07-15 10:50:38",
                        "version": "1.0.1",
                        "url":
                            "https://gitlab.com/packagecontrol-test/package_control-tester"
                            "/-/archive/win-1.0.1/package_control-tester-win-1.0.1.zip"
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_tags(self, extra_settings, url, tag_prefix, result):
        client = GitLabClient(self.settings(extra_settings))
        self.assertEqual(result, client.download_info_from_tags(url, tag_prefix))

    @data(
        (
            (
                # url
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                # asset_templates
                [
                    # asset name pattern, { selectors }
                    ("package_control-tester.sublime-package", {}),
                ],
                # tag prefix
                None,
                # results (note: test repo"s don"t provide release assests to test against, unfortunatelly)
                [
                    # {
                    #     "date": "2020-07-15 10:50:38",
                    #     "version": "1.0.1",
                    #     "url":
                    #         "https://gitlab.com/packagecontrol-test/package_control-tester"
                    #         "/-/releases/1.0.1/downloads/package_control-tester.sublime-package"
                    # }
                ]
            ),
            (
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-st4???.sublime-package",
                        {"sublime_text": ">=4107"}
                    )
                ],
                None,
                []
            ),
            (
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-st${st_build}.sublime-package",
                        {"sublime_text": ">=4107"}
                    )
                ],
                None,
                []
            ),
            (
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-${platform}.sublime-package",
                        {"platforms": ["*"]}
                    )
                ],
                None,
                []
            ),
            (
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-${platform}.sublime-package",
                        {"platforms": ["windows-x64", "linux-x64"]}
                    )
                ],
                None,
                []
            ),
            (
                "https://gitlab.com/packagecontrol-test/package_control-tester",
                [
                    (
                        "package_control-tester-win-amd64.sublime-package",
                        {"platforms": ["windows-x64"]}
                    ),
                    (
                        "package_control-tester-win-arm64.sublime-package",
                        {"platforms": ["windows-arm64"]}
                    ),
                    (
                        "package_control-tester-linux-aarch64.sublime-package",
                        {"platforms": ["linux-arm64"]}
                    )
                ],
                None,
                []
            ),
        )
    )
    def download_info_from_releases(self, url, asset_templates, tag_prefix, result):
        client = GitLabClient(self.settings())
        self.assertEqual(result, client.download_info_from_releases(url, asset_templates, tag_prefix))


@data_decorator
class PyPiClientTests(unittest.TestCase):
    maxDiff = None

    def settings(self, extra=None):
        settings = {
            "debug": DEBUG,
            "cache": HttpCache(604800),
            "cache_length": 604800,
            "user_agent": USER_AGENT
        }
        if extra:
            settings.update(extra)

        return settings

    @data(
        (
            (
                "01",
                "https://pypi.org",
                (None, None)
            ),
            (
                "02",
                "https://pypi.org/",
                (None, None)
            ),
            (
                "03",
                "https://pypi.org/project",
                (None, None)
            ),
            (
                "latest",
                "https://pypi.org/project/coverage",
                ("coverage", None)
            ),
            (
                "pinned",
                "https://pypi.org/project/coverage/4.0",
                ("coverage", "4.0")
            ),
            (
                "invalid_domain",
                "https://pypi;org/project/coverage",
                (None, None)
            ),
        ),
        first_param_name_suffix=True
    )
    def name_and_version(self, url, result):
        client = PyPiClient(self.settings())
        self.assertEqual(result, client.name_and_version(url))

    @data((("https://pypi.org/project/coverage", None),))
    def download_info(self, url, result):
        client = PyPiClient(self.settings())
        self.assertEqual(result, client.download_info(url))

    @data((("https://pypi.org/project/coverage", None),))
    def download_info_from_branch(self, url, result):
        client = PyPiClient(self.settings())
        self.assertEqual(result, client.download_info_from_branch(url))

    @data((("https://pypi.org/project/coverage", None),))
    def download_info_from_tags(self, url, result):
        client = PyPiClient(self.settings())
        self.assertEqual(result, client.download_info_from_tags(url))

    @data(
        (
            (
                # name
                "01",
                # url
                "https://pypi.org/project/coverage/4.0",
                # asset_templates
                [
                    # asset name pattern, { selectors }
                    (
                        "coverage-*-cp33-*-macosx_*_x86_64*.whl",
                        {
                            "platforms": ["osx-x64"],
                            "python_versions": ["3.3"]
                        }
                    ),
                    (
                        "coverage-*-cp33-*-win_amd64*.whl",
                        {
                            "platforms": ["windows-x64"],
                            "python_versions": ["3.3"]
                        }
                    )
                ],
                # results (note: test repo"s don"t provide release assests to test against, unfortunatelly)
                [
                    {
                        "date": "2015-09-20 15:40:43",
                        "version": "4.0",
                        "url": "https://files.pythonhosted.org/packages/98/4c"
                               "/21b72fb43ad3023f58290195f6c2504982bc20ce68036fc6136d2888b3fd"
                               "/coverage-4.0-cp33-cp33m-macosx_10_10_x86_64.whl",
                        "sha256": "b442440565e6a89dcf36a005fe50cdf235bc3c0dd23982d3bdb5fe4cd491d112",
                        "platforms": ["osx-x64"],
                        "python_versions": ["3.3"]
                    },
                    {
                        "date": "2015-09-20 15:40:53",
                        "version": "4.0",
                        "url": "https://files.pythonhosted.org/packages/09/30"
                               "/7af800f04ec49b1aaa81d9f5aa69f2d81ee988ead17fb8d98121ba32b8d2"
                               "/coverage-4.0-cp33-none-win_amd64.whl",
                        "sha256": "fb4cbddbd0fcdc87df84f612c65f0240bfa60e595dea1666401817c10064ae31",
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.3"]
                    }
                ]
            ),
            (
                "02",
                "https://pypi.org/project/coverage/4.0",
                [
                    (
                        "coverage-?.?-cp33-*-macosx_??_??_x86_64.whl",
                        {
                            "platforms": ["osx-x64"],
                            "python_versions": ["3.3"]
                        }
                    ),
                    (
                        "coverage-?.?-cp33-*-win_amd64.whl",
                        {
                            "platforms": ["windows-x64"],
                            "python_versions": ["3.3"]
                        }
                    )
                ],
                [
                    {
                        "date": "2015-09-20 15:40:43",
                        "version": "4.0",
                        "url": "https://files.pythonhosted.org/packages/98/4c"
                               "/21b72fb43ad3023f58290195f6c2504982bc20ce68036fc6136d2888b3fd"
                               "/coverage-4.0-cp33-cp33m-macosx_10_10_x86_64.whl",
                        "sha256": "b442440565e6a89dcf36a005fe50cdf235bc3c0dd23982d3bdb5fe4cd491d112",
                        "platforms": ["osx-x64"],
                        "python_versions": ["3.3"]
                    },
                    {
                        "date": "2015-09-20 15:40:53",
                        "version": "4.0",
                        "url": "https://files.pythonhosted.org/packages/09/30"
                               "/7af800f04ec49b1aaa81d9f5aa69f2d81ee988ead17fb8d98121ba32b8d2"
                               "/coverage-4.0-cp33-none-win_amd64.whl",
                        "sha256": "fb4cbddbd0fcdc87df84f612c65f0240bfa60e595dea1666401817c10064ae31",
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.3"]
                    }
                ]
            ),
            (
                "03",
                "https://pypi.org/project/coverage/4.0",
                [
                    (
                        "coverage-${version}-cp${py_version}-*-macosx_*_x86_64.whl",
                        {
                            "platforms": ["osx-x64"],
                            "python_versions": ["3.3"]
                        }
                    ),
                    (
                        "coverage-${version}-cp${py_version}-*-win_amd64.whl",
                        {
                            "platforms": ["windows-x64"],
                            "python_versions": ["3.3"]
                        }
                    )
                ],
                [
                    {
                        "date": "2015-09-20 15:40:43",
                        "version": "4.0",
                        "url": "https://files.pythonhosted.org/packages/98/4c"
                               "/21b72fb43ad3023f58290195f6c2504982bc20ce68036fc6136d2888b3fd"
                               "/coverage-4.0-cp33-cp33m-macosx_10_10_x86_64.whl",
                        "sha256": "b442440565e6a89dcf36a005fe50cdf235bc3c0dd23982d3bdb5fe4cd491d112",
                        "platforms": ["osx-x64"],
                        "python_versions": ["3.3"]
                    },
                    {
                        "date": "2015-09-20 15:40:53",
                        "version": "4.0",
                        "url": "https://files.pythonhosted.org/packages/09/30"
                               "/7af800f04ec49b1aaa81d9f5aa69f2d81ee988ead17fb8d98121ba32b8d2"
                               "/coverage-4.0-cp33-none-win_amd64.whl",
                        "platforms": ["windows-x64"],
                        "sha256": "fb4cbddbd0fcdc87df84f612c65f0240bfa60e595dea1666401817c10064ae31",
                        "python_versions": ["3.3"]
                    }
                ]
            ),
        ),
        first_param_name_suffix=True
    )
    def download_info_from_releases(self, url, asset_templates, result):
        client = PyPiClient(self.settings())
        self.assertEqual(result, client.download_info_from_releases(url, asset_templates))
