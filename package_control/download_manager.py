try:
    # Python 3
    from urllib.parse import urlparse
    import urllib.request as urllib_compat
except (ImportError):
    # Python 2
    from urlparse import urlparse
    import urllib2 as urllib_compat

import sys
import re
import socket

from .show_error import show_error
from .console_write import console_write
from .cache import set_cache, get_cache
from .unicode import unicode_from_os

from .downloaders.urllib_downloader import UrlLibDownloader
from .downloaders.wget_downloader import WgetDownloader
from .downloaders.curl_downloader import CurlDownloader
from .downloaders.binary_not_found_error import BinaryNotFoundError
from .downloaders.rate_limit_exception import RateLimitException
from .http_cache import HttpCache


class DownloadManager(object):
    def __init__(self, settings):
        self.settings = settings
        if settings.get('http_cache'):
            cache_length = settings.get('http_cache_length', 86400)
            self.settings['cache'] = HttpCache(cache_length)

    def fetch(self, url, error_message):
        """
        Downloads a URL and returns the contents

        :param url:
            The string URL to download

        :param error_message:
            The error message to include if the download fails

        :return:
            The string contents of the URL, or False on error
        """

        has_ssl = 'ssl' in sys.modules and hasattr(urllib_compat, 'HTTPSHandler')
        is_ssl = re.search('^https://', url) != None
        downloader = None

        if (is_ssl and has_ssl) or not is_ssl:
            downloader = UrlLibDownloader(self.settings)
        else:
            for downloader_class in [CurlDownloader, WgetDownloader]:
                try:
                    downloader = downloader_class(self.settings)
                    break
                except (BinaryNotFoundError):
                    pass

        if not downloader:
            show_error(u'Unable to download %s due to no ssl module available and no capable program found. Please install curl or wget.' % url)
            return False

        url = url.replace(' ', '%20')
        hostname = urlparse(url).hostname.lower()
        timeout = self.settings.get('timeout', 3)

        rate_limited_domains = get_cache('rate_limited_domains', [])

        if self.settings.get('debug'):
            try:
                ip = socket.gethostbyname(hostname)
            except (socket.gaierror) as e:
                ip = unicode_from_os(e)

            console_write(u"Download Debug", True)
            console_write(u"  URL: %s" % url)
            console_write(u"  Resolved IP: %s" % ip)
            console_write(u"  Timeout: %s" % str(timeout))

        if hostname in rate_limited_domains:
            if self.settings.get('debug'):
                console_write(u"  Skipping due to hitting rate limit for %s" % hostname)
            return False

        try:
            return downloader.download(url, error_message, timeout, 3)
        except (RateLimitException) as e:

            rate_limited_domains.append(hostname)
            set_cache('rate_limited_domains', rate_limited_domains, self.settings.get('cache_length'))

            error_string = (u'Hit rate limit of %s for %s, skipping all futher ' +
                u'download requests for this domain') % (e.limit, e.host)
            console_write(error_string, True)

        return False
