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

    def fetch(self, url, prefer_cached=False):
        """
        Retrieves the contents of a URL

        :param url:
            The URL to download the content from

        :param prefer_cached:
            If a cached copy of the content is preferred

        :return: The bytes/string, or False on error
        """

        # If there are extra params for the domain name, add them
        extra_params = self.settings.get('query_string_params')
        domain_name = urlparse(url).netloc
        if extra_params and domain_name in extra_params:
            params = urlencode(extra_params[domain_name])
            joiner = '?%s' if url.find('?') == -1 else '&%s'
            url += joiner % params

        download_manager = grab(url, self.settings)
        content = download_manager.fetch(url,
            'Error downloading repository.', prefer_cached)
        release(url, download_manager)
        return content

    def fetch_json(self, url, prefer_cached=False):
        """
        Retrieves and parses the JSON from a URL

        :param url:
            The URL to download the JSON from

        :param prefer_cached:
            If a cached copy of the JSON is preferred

        :return: A dict or list from the JSON, or False on error
        """

        repository_json = self.fetch(url, prefer_cached)
        if repository_json == False:
            return False
        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            console_write(u'Error parsing JSON from repository %s.' % url, True)
        return False
