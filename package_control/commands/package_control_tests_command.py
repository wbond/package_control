import sublime_plugin

from ..tests import runner
from ..tests.clients import GitHubClientTests, BitBucketClientTests
from ..tests.providers import GitHubRepositoryProviderTests, BitBucketRepositoryProviderTests, GitHubUserProviderTests, RepositoryProviderTests, ChannelProviderTests


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
                RepositoryProviderTests,
                ChannelProviderTests
            ]
        )
