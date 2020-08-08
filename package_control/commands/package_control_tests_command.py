import sublime
import sublime_plugin

from ..tests import runner
from ..tests.clients import GitHubClientTests, BitBucketClientTests
from ..tests.providers import (
    BitBucketRepositoryProviderTests,
    ChannelProviderTests,
    GitHubRepositoryProviderTests,
    GitHubUserProviderTests,
    GitLabRepositoryProviderTests,
    GitLabUserProviderTests,
    RepositoryProviderTests,
)


class PackageControlTestsCommand(sublime_plugin.WindowCommand):
    """
    A command to run the tests for Package Control
    """

    def run(self):
        runner(
            self.window,
            [
                GitHubClientTests,
                BitBucketClientTests,
                GitHubRepositoryProviderTests,
                BitBucketRepositoryProviderTests,
                GitHubUserProviderTests,
                GitLabRepositoryProviderTests,
                GitLabUserProviderTests,
                RepositoryProviderTests,
                ChannelProviderTests
            ]
        )

    def is_visible(self):
        settings = sublime.load_settings('Package Control.sublime-settings')
        return settings.get('enable_tests', False)
