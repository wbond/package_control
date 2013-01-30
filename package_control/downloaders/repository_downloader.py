import threading

from ..providers.bitbucket_package_provider import BitBucketPackageProvider
from ..providers.github_package_provider import GitHubPackageProvider
from ..providers.github_user_provider import GitHubUserProvider
from ..providers.package_provider import PackageProvider


# The providers (in order) to check when trying to download repository info
_package_providers = [BitBucketPackageProvider, GitHubPackageProvider,
    GitHubUserProvider, PackageProvider]


class RepositoryDownloader(threading.Thread):
    """
    Downloads information about a repository in the background

    :param package_manager:
        An instance of :class:`PackageManager` used to download files

    :param name_map:
        The dict of name mapping for URL slug -> package name

    :param repo:
        The URL of the repository to download info about
    """

    def __init__(self, package_manager, name_map, repo):
        self.package_manager = package_manager
        self.repo = repo
        self.packages = {}
        self.name_map = name_map
        threading.Thread.__init__(self)

    def run(self):
        for provider_class in _package_providers:
            provider = provider_class(self.repo, self.package_manager)
            if provider.match_url():
                break
        packages = provider.get_packages()
        if packages == False:
            self.packages = False
            return

        mapped_packages = {}
        for package in list(packages.keys()):
            mapped_package = self.name_map.get(package, package)
            mapped_packages[mapped_package] = packages[package]
            mapped_packages[mapped_package]['name'] = mapped_package
        packages = mapped_packages

        self.packages = packages
        self.renamed_packages = provider.get_renamed_packages()
        self.unavailable_packages = provider.get_unavailable_packages()
