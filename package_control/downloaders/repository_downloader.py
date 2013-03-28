import threading

from ..providers import REPOSITORY_PROVIDERS


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
        for provider_class in REPOSITORY_PROVIDERS:
            if provider_class.match_url(self.repo):
                provider = provider_class(self.repo, self.settings)
                break

        packages = provider.get_packages()
        if packages == False:
            self.packages = False
            return

        self.packages = {}  
        for name, info in packages.items():

            # Allow name mapping of packages for schema version < 2.0
            name = self.name_map.get(name, name)
            info['name'] = name

            self.packages[name] = info

        self.renamed_packages = provider.get_renamed_packages()
        self.unavailable_packages = provider.get_unavailable_packages()
