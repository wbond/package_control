import json

from urllib.parse import urlencode, urlparse

from ..download_manager import downloader
from .client_exception import ClientException


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
            url += ('&' if '?' in url else '?') + urlencode(extra_params[domain_name])

        with downloader(url, self.settings) as manager:
            content = manager.fetch(url, 'Error downloading repository.', prefer_cached)
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
        except ValueError:
            raise ClientException('Error parsing JSON from URL %s.' % url)
