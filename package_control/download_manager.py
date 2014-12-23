import sys
import re
import socket
from threading import Lock, Timer
from contextlib import contextmanager

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

from . import __version__

from .show_error import show_error
from .console_write import console_write
from .cache import set_cache, get_cache
from .unicode import unicode_from_os

from .downloaders import DOWNLOADERS
from .downloaders.urllib_downloader import UrlLibDownloader
from .downloaders.binary_not_found_error import BinaryNotFoundError
from .downloaders.rate_limit_exception import RateLimitException
from .downloaders.downloader_exception import DownloaderException
from .downloaders.win_downloader_exception import WinDownloaderException
from .http_cache import HttpCache


# A dict of domains - each points to a list of downloaders
_managers = {}

# How many managers are currently checked out
_in_use = 0

# Make sure connection management doesn't run into threading issues
_lock = Lock()

# A timer used to disconnect all managers after a period of no usage
_timer = None


@contextmanager
def downloader(url, settings):
    try:
        manager = None
        manager = _grab(url, settings)
        yield manager

    finally:
        if manager:
            _release(url, manager)


def _grab(url, settings):
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        if _timer:
            _timer.cancel()
            _timer = None

        parsed = urlparse(url)
        if not parsed or not parsed.hostname:
            raise DownloaderException(u'The URL "%s" is malformed' % url)
        hostname = parsed.hostname.lower()
        if hostname not in _managers:
            _managers[hostname] = []

        if not _managers[hostname]:
            _managers[hostname].append(DownloadManager(settings))

        _in_use += 1

        return _managers[hostname].pop()

    finally:
        _lock.release()


def _release(url, manager):
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        hostname = urlparse(url).hostname.lower()

        # This means the package was reloaded between _grab and _release,
        # so the downloader is using old code and we want to discard it
        if hostname not in _managers:
            return

        _managers[hostname].insert(0, manager)

        _in_use -= 1

        if _timer:
            _timer.cancel()
            _timer = None

        if _in_use == 0:
            _timer = Timer(5.0, close_all_connections)
            _timer.start()

    finally:
        _lock.release()


def close_all_connections():
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        if _timer:
            _timer.cancel()
            _timer = None

        for domain, managers in _managers.items():
            for manager in managers:
                manager.close()
        _managers = {}

    finally:
        _lock.release()


def update_url(url, debug):
    """
    Takes an old, out-dated URL and updates it. Mostly used with GitHub URLs
    since they tend to be constantly evolving their infrastructure.

    :param url:
        The URL to update

    :param debug:
        If debugging is enabled

    :return:
        The updated URL
    """

    if not url:
        return url

    original_url = url
    url = url.replace('://raw.github.com/', '://raw.githubusercontent.com/')
    url = url.replace('://nodeload.github.com/', '://codeload.github.com/')
    url = re.sub('^(https://codeload.github.com/[^/]+/[^/]+/)zipball(/.*)$', '\\1zip\\2', url)

    # Fix URLs from old versions of Package Control since we are going to
    # remove all packages but Package Control from them to force upgrades
    if url == 'https://sublime.wbond.net/repositories.json' or url == 'https://sublime.wbond.net/channel.json':
        url = 'https://packagecontrol.io/channel_v3.json'

    if debug and url != original_url:
        console_write(u'Fixed URL from %s to %s' % (original_url, url), True)

    return url


class DownloadManager(object):
    def __init__(self, settings):
        # Cache the downloader for re-use
        self.downloader = None

        user_agent = settings.get('user_agent')
        if user_agent and user_agent.find('%s') != -1:
            settings['user_agent'] = user_agent % __version__

        self.settings = settings
        if settings.get('http_cache'):
            cache_length = settings.get('http_cache_length', 604800)
            self.settings['cache'] = HttpCache(cache_length)

    def close(self):
        if self.downloader:
            self.downloader.close()
            self.downloader = None

    def fetch(self, url, error_message, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        :param url:
            The string URL to download

        :param error_message:
            The error message to include if the download fails

        :param prefer_cached:
            If cached version of the URL content is preferred over a new request

        :raises:
            DownloaderException: if there was an error downloading the URL

        :return:
            The string contents of the URL
        """

        is_ssl = re.search('^https://', url) != None

        url = update_url(url, self.settings.get('debug'))

        # Make sure we have a downloader, and it supports SSL if we need it
        if not self.downloader or (is_ssl and not self.downloader.supports_ssl()):
            for downloader_class in DOWNLOADERS:
                try:
                    downloader = downloader_class(self.settings)
                    if is_ssl and not downloader.supports_ssl():
                        continue
                    self.downloader = downloader
                    break
                except (BinaryNotFoundError):
                    pass

        if not self.downloader:
            error_string = u'Unable to download %s due to no ssl module available and no capable program found. Please install curl or wget.' % url
            show_error(error_string)
            raise DownloaderException(error_string)

        url = url.replace(' ', '%20')
        hostname = urlparse(url).hostname
        if hostname:
            hostname = hostname.lower()
        timeout = self.settings.get('timeout', 3)

        rate_limited_domains = get_cache('rate_limited_domains', [])

        if self.settings.get('debug'):
            try:
                port = 443 if is_ssl else 80
                ipv6_info = socket.getaddrinfo(hostname, port, socket.AF_INET6)
                if ipv6_info:
                    ipv6 = ipv6_info[0][4][0]
                else:
                    ipv6 = None
            except (socket.gaierror) as e:
                ipv6 = None
            except (TypeError) as e:
                ipv6 = None

            try:
                ip = socket.gethostbyname(hostname)
            except (socket.gaierror) as e:
                ip = unicode_from_os(e)
            except (TypeError) as e:
                ip = None

            console_write(u"Download Debug", True)
            console_write(u"  URL: %s" % url)
            if ipv6:
                console_write(u"  Resolved IPv6: %s" % ipv6)
            console_write(u"  Resolved IP: %s" % ip)
            console_write(u"  Timeout: %s" % str(timeout))

        if hostname in rate_limited_domains:
            error_string = u"Skipping due to hitting rate limit for %s" % hostname
            if self.settings.get('debug'):
                console_write(u"  %s" % error_string)
            raise DownloaderException(error_string)

        try:
            return self.downloader.download(url, error_message, timeout, 3, prefer_cached)

        except (RateLimitException) as e:

            rate_limited_domains.append(hostname)
            set_cache('rate_limited_domains', rate_limited_domains, self.settings.get('cache_length'))

            error_string = (u'Hit rate limit of %s for %s, skipping all futher ' +
                u'download requests for this domain') % (e.limit, e.domain)
            console_write(error_string, True)
            raise

        except (WinDownloaderException) as e:

            error_string = (u'Attempting to use Urllib downloader due to WinINet error: %s') % e
            console_write(error_string, True)

            # Here we grab the proxy info extracted from WinInet to fill in
            # the Package Control settings if those are not present. This should
            # hopefully make a seamless fallback for users who run into weird
            # windows errors related to network communication.
            wininet_proxy          = self.downloader.proxy or ''
            wininet_proxy_username = self.downloader.proxy_username or ''
            wininet_proxy_password = self.downloader.proxy_password or ''

            http_proxy     = self.settings.get('http_proxy', '')
            https_proxy    = self.settings.get('https_proxy', '')
            proxy_username = self.settings.get('proxy_username', '')
            proxy_password = self.settings.get('proxy_password', '')

            settings = self.settings.copy()
            if not http_proxy and wininet_proxy:
                settings['http_proxy'] = wininet_proxy
            if not https_proxy and wininet_proxy:
                settings['https_proxy'] = wininet_proxy

            has_proxy = settings.get('http_proxy') or settings.get('https_proxy')
            if has_proxy and not proxy_username and wininet_proxy_username:
                settings['proxy_username'] = wininet_proxy_username
            if has_proxy and not proxy_password and wininet_proxy_password:
                settings['proxy_password'] = wininet_proxy_password

            self.downloader = UrlLibDownloader(settings)
            # Try again with the new downloader!
            return self.fetch(url, error_message, prefer_cached)
