import threading

from ..providers.bitbucket_package_provider import BitBucketPackageProvider
from ..providers.github_package_provider import GitHubPackageProvider
from ..providers.github_user_provider import GitHubUserProvider
from ..providers.package_provider import PackageProvider


# The providers (in order) to check when trying to download repository info
_repository_providers = [BitBucketPackageProvider, GitHubPackageProvider,
    GitHubUserProvider, PackageProvider]


class RepositoryDownloader(threading.Thread):
    """
    Downloads information about a repository in the background

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`,
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`

    :param name_map:
        The dict of name mapping for URL slug -> package name

    :param repo:
        The URL of the repository to download info about
    """

    def __init__(self, settings, name_map, repo):
        self.settings = settings
        self.repo = repo
        self.packages = {}
        self.name_map = name_map
        threading.Thread.__init__(self)

    def run(self):
        for provider_class in _repository_providers:
            provider = provider_class(self.repo, self.settings)
            if provider.match_url():
                break
        packages = provider.get_packages()
        if packages == False:
            self.packages = False
            return

        self.packages = {}  
        for package in packages:

            # Allow name mapping of packages for schema version < 2.0
            package_name = self.name_map.get(package['name'], package['name'])
            package['name'] = package_name

            self.packages[package_name] = package

        self.renamed_packages = provider.get_renamed_packages()
        self.unavailable_packages = provider.get_unavailable_packages()
