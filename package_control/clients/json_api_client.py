import json

from ..console_write import console_write
from ..download_manager import DownloadManager


class JSONApiClient():
    def __init__(self, settings):
        self.settings = settings

    def fetch_json(self, url):
        """
        Retrieves and parses the JSON from a URL

        :return: A dict or list from the JSON, or False on error
        """

        download_manager = DownloadManager(self.settings)
        repository_json = download_manager.fetch(url,
            'Error downloading repository.')
        if repository_json == False:
            return False
        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            console_write(u'Error parsing JSON from repository %s.' % url, True)
        return False