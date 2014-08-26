import threading


class BackgroundDownloader(threading.Thread):
    """
    Downloads information from one or more URLs in the background.
    Normal usage is to use one BackgroundDownloader per domain name.

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

    :param providers:
        An array of providers that can download the URLs
    """

    def __init__(self, settings, providers):
        self.settings = settings
        self.urls = []
        self.providers = providers
        self.used_providers = {}
        threading.Thread.__init__(self)

    def add_url(self, url):
        """
        Adds a URL to the list to download

        :param url:
            The URL to download info about
        """

        self.urls.append(url)

    def get_provider(self, url):
        """
        Returns the provider for the URL specified

        :param url:
            The URL to return the provider for

        :return:
            The provider object for the URL
        """

        return self.used_providers.get(url)

    def run(self):
        for url in self.urls:
            for provider_class in self.providers:
                if provider_class.match_url(url):
                    provider = provider_class(url, self.settings)
                    break

            provider.prefetch()
            self.used_providers[url] = provider
