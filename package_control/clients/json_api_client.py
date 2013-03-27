try:
    # Python 3
    from urllib.parse import urlencode
except (ImportError):
    # Python 2
    from urllib import urlencode

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

        if 'query_string_params' in self.settings:
            params = urlencode(self.settings['query_string_params'])
            joiner = '?%s' if url.find('?') == -1 else '&%s'
            url += joiner % params

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
