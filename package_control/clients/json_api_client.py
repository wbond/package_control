import json

try:
    # Python 3
    from urllib.parse import urlencode, urlparse
except (ImportError):
    # Python 2
    from urllib import urlencode
    from urlparse import urlparse

from ..console_write import console_write
from ..download_manager import grab, release


class JSONApiClient():
    def __init__(self, settings):
        self.settings = settings

    def fetch_json(self, url):
        """
        Retrieves and parses the JSON from a URL

        :return: A dict or list from the JSON, or False on error
        """

        # If there are extra params for the domain name, add them
        extra_params = self.settings.get('query_string_params')
        domain_name = urlparse(url).netloc
        if extra_params and domain_name in extra_params:
            params = urlencode(extra_params[domain_name])
            joiner = '?%s' if url.find('?') == -1 else '&%s'
            url += joiner % params

        download_manager = grab(url, self.settings)
        repository_json = download_manager.fetch(url,
            'Error downloading repository.')
        release(url, download_manager)
        if repository_json == False:
            return False
        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            console_write(u'Error parsing JSON from repository %s.' % url, True)
        return False
