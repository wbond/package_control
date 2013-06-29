import sys
import re
import socket
from threading import Lock, Timer

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
from .downloaders.binary_not_found_error import BinaryNotFoundError
from .downloaders.rate_limit_exception import RateLimitException
from .http_cache import HttpCache


# A dict of domains - each points to a list of downloaders
_managers = {}

# How many managers are currently checked out
_in_use = 0

# Make sure connection management doesn't run into threading issues
_lock = Lock()

# A timer used to disconnect all managers after a period of no usage
_timer = None


def grab(url, settings):
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        if _timer:
            _timer.cancel()
            _timer = None

        hostname = urlparse(url).hostname.lower()
        if hostname not in _managers:
            _managers[hostname] = []

        if not _managers[hostname]:
            _managers[hostname].append(DownloadManager(settings))

        _in_use += 1

        return _managers[hostname].pop()

    finally:
        _lock.release()


def release(url, manager):
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        hostname = urlparse(url).hostname.lower()
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

        :return:
            The string contents of the URL, or False on error
        """

        is_ssl = re.search('^https://', url) != None

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
            return self.downloader.download(url, error_message, timeout, 3, prefer_cached)
        except (RateLimitException) as e:

            rate_limited_domains.append(hostname)
            set_cache('rate_limited_domains', rate_limited_domains, self.settings.get('cache_length'))

            error_string = (u'Hit rate limit of %s for %s, skipping all futher ' +
                u'download requests for this domain') % (e.limit, e.host)
            console_write(error_string, True)

        return False
