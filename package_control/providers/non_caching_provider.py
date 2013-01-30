import json

from ..console_write import console_write


class NonCachingProvider():
    """
    Base for package providers that do not need to cache the JSON
    """

    def fetch_json(self, url):
        """
        Retrieves and parses the JSON from a URL

        :return: A dict or list from the JSON, or False on error
        """

        repository_json = self.package_manager.download_url(url,
            'Error downloading repository.')
        if repository_json == False:
            return False
        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            console_write(u'Error parsing JSON from repository %s.' % url, True)
        return False

    def get_unavailable_packages(self):
        """
        Method for compatibility with PackageProvider class. These providers
        are based on API calls, and thus do not support different platform
        downloads, making it impossible for there to be unavailable packages.

        :return: An empty list
        """

        return []
