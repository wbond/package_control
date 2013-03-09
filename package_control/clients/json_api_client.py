import json

from ..console_write import console_write


class JSONApiClient():
    def __init__(self, package_manager):
        self.package_manager = package_manager

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