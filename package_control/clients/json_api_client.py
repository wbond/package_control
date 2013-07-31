import json

try:
    # Python 3
    from urllib.parse import urlencode, urlparse
except (ImportError):
    # Python 2
    from urllib import urlencode
    from urlparse import urlparse

from .client_exception import ClientException
from ..download_manager import downloader


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

        :return: The bytes/string
        """

        # If there are extra params for the domain name, add them
        extra_params = self.settings.get('query_string_params')
        domain_name = urlparse(url).netloc
        if extra_params and domain_name in extra_params:
            params = urlencode(extra_params[domain_name])
            joiner = '?%s' if url.find('?') == -1 else '&%s'
            url += joiner % params

        with downloader(url, self.settings) as manager:
            content = manager.fetch(url, 'Error downloading repository.',
                prefer_cached)
        return content

    def fetch_json(self, url, prefer_cached=False):
        """
        Retrieves and parses the JSON from a URL

        :param url:
            The URL to download the JSON from

        :param prefer_cached:
            If a cached copy of the JSON is preferred

        :return: A dict or list from the JSON
        """

        repository_json = self.fetch(url, prefer_cached)

        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            error_string = u'Error parsing JSON from URL %s.' % url
            raise ClientException(error_string)
