import os
import re
import socket
import sys
from threading import Lock, Timer
from urllib.parse import urljoin, urlparse

from . import __version__
from . import text
from .cache import set_cache, get_cache
from .console_write import console_write
from .show_error import show_error

from .downloaders import DOWNLOADERS
from .downloaders.binary_not_found_error import BinaryNotFoundError
from .downloaders.downloader_exception import DownloaderException
from .downloaders.oscrypto_downloader_exception import OscryptoDownloaderException
from .downloaders.rate_limit_exception import RateLimitException
from .downloaders.rate_limit_exception import RateLimitSkipException
from .downloaders.urllib_downloader import UrlLibDownloader
from .downloaders.win_downloader_exception import WinDownloaderException
from .http_cache import HttpCache


_managers = {}
"""A dict of domains - each points to a list of downloaders"""

_in_use = 0
"""How many managers are currently checked out"""

_lock = Lock()
"""Make sure connection management doesn't run into threading issues"""

_timer = None
"""A timer used to disconnect all managers after a period of no usage"""


def http_get(url, settings, error_message='', prefer_cached=False):
    """
    Performs a HTTP GET request using best matching downloader.

    :param url:
        The string URL to download

    :param settings:
        The dictionary with downloader settings.

          - ``debug``
          - ``downloader_precedence``
          - ``http_basic_auth``
          - ``http_cache``
          - ``http_cache_length``
          - ``http_proxy``
          - ``https_proxy``
          - ``proxy_username``
          - ``proxy_password``
          - ``user_agent``
          - ``timeout``

    :param error_message:
        The error message to include if the download fails

    :param prefer_cached:
        If cached version of the URL content is preferred over a new request

    :raises:
        DownloaderException: if there was an error downloading the URL

    :return:
        The string contents of the URL
    """

    manager = None
    result = None

    try:
        manager = _grab(url, settings)
        result = manager.fetch(url, error_message, prefer_cached)

    finally:
        if manager:
            _release(url, manager)

    return result


def _grab(url, settings):
    global _managers, _lock, _in_use, _timer

    with _lock:
        if _timer:
            _timer.cancel()
            _timer = None

        parsed = urlparse(url)
        if not parsed or not parsed.hostname:
            raise DownloaderException('The URL "%s" is malformed' % url)
        hostname = parsed.hostname.lower()
        if hostname not in _managers:
            _managers[hostname] = []

        if not _managers[hostname]:
            _managers[hostname].append(DownloadManager(settings))

        _in_use += 1

        return _managers[hostname].pop()


def _release(url, manager):
    global _managers, _lock, _in_use, _timer

    with _lock:
        parsed = urlparse(url)
        if not parsed or not parsed.hostname:
            raise DownloaderException('The URL "%s" is malformed' % url)
        hostname = parsed.hostname.lower()

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


def close_all_connections():
    global _managers, _lock, _in_use, _timer

    with _lock:
        if _timer:
            _timer.cancel()
            _timer = None

        for managers in _managers.values():
            for manager in managers:
                manager.close()
        _managers = {}


def resolve_urls(root_url, uris):
    """
    Convert a list of relative uri's to absolute urls/paths.

    :param root_url:
        The root url string

    :param uris:
        An iteratable of relative uri's to resolve.

    :returns:
        A generator of resolved URLs
    """

    scheme_match = re.match(r'(https?:)//', root_url, re.I)
    if scheme_match is None:
        root_dir = os.path.dirname(root_url)
    else:
        root_dir = ''

    for url in uris:
        if url.startswith('//'):
            if scheme_match is not None:
                url = scheme_match.group(1) + url
            else:
                url = 'https:' + url
        elif url.startswith('/'):
            # We don't allow absolute repositories
            continue
        elif url.startswith('./') or url.startswith('../'):
            if root_dir:
                url = os.path.normpath(os.path.join(root_dir, url))
            else:
                url = urljoin(root_url, url)
        yield url


def resolve_url(root_url, url):
    """
    Convert a list of relative uri's to absolute urls/paths.

    :param root_url:
        The root url string

    :param uris:
        An iteratable of relative uri's to resolve.

    :returns:
        A generator of resolved URLs
    """

    scheme_match = re.match(r'(https?:)//', root_url, re.I)
    if scheme_match is None:
        root_dir = os.path.dirname(root_url)
    else:
        root_dir = ''

    if url.startswith('//'):
        if scheme_match is not None:
            return scheme_match.group(1) + url
        else:
            return 'https:' + url

    elif url.startswith('./') or url.startswith('../'):
        if root_dir:
            return os.path.normpath(os.path.join(root_dir, url))
        else:
            return urljoin(root_url, url)

    return url


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
    url = re.sub(r'^(https://codeload\.github\.com/[^/#?]+/[^/#?]+/)zipball(/.*)$', '\\1zip\\2', url)

    # Fix URLs from old versions of Package Control since we are going to
    # remove all packages but Package Control from them to force upgrades
    if url == 'https://sublime.wbond.net/repositories.json' or url == 'https://sublime.wbond.net/channel.json':
        url = 'https://packagecontrol.io/channel_v3.json'

    if debug and url != original_url:
        console_write(
            '''
            Fixed URL from %s to %s
            ''',
            (original_url, url)
        )

    return url


class DownloadManager:

    def __init__(self, settings):
        # Cache the downloader for re-use
        self.downloader = None

        keys_to_copy = {
            'debug',
            'downloader_precedence',
            'http_basic_auth',
            'http_proxy',
            'https_proxy',
            'proxy_username',
            'proxy_password',
            'user_agent',
            'timeout',
        }

        # Copy required settings to avoid manipulating caller's environment.
        # It's needed as e.g. `cache_length` is defined with different meaning in PackageManager's
        # settings. Also `cache` object shouldn't be propagated to caller.
        self.settings = {key: value for key, value in settings.items() if key in keys_to_copy}

        # add package control version to user agent
        user_agent = self.settings.get('user_agent')
        if user_agent and '%s' in user_agent:
            self.settings['user_agent'] = user_agent % __version__

        # setup private http cache storage driver
        if settings.get('http_cache'):
            cache_length = settings.get('http_cache_length', 604800)
            self.settings['cache'] = HttpCache(cache_length)
            self.settings['cache_length'] = cache_length

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

        is_ssl = re.search('^https://', url) is not None

        url = update_url(url, self.settings.get('debug'))

        # We don't use sublime.platform() here since this is used for
        # the crawler on packagecontrol.io also
        if sys.platform == 'darwin':
            platform = 'osx'
        elif sys.platform == 'win32':
            platform = 'windows'
        else:
            platform = 'linux'

        downloader_precedence = self.settings.get(
            'downloader_precedence',
            {
                "windows": ["wininet", "oscrypto", "urllib"],
                "osx": ["urllib", "oscrypto", "curl"],
                "linux": ["urllib", "oscrypto", "curl", "wget"]
            }
        )
        downloader_list = downloader_precedence.get(platform, [])

        if not isinstance(downloader_list, list) or len(downloader_list) == 0:
            error_string = text.format(
                '''
                No list of preferred downloaders specified in the
                "downloader_precedence" setting for the platform "%s"
                ''',
                platform
            )
            show_error(error_string)
            raise DownloaderException(error_string)

        # Make sure we have a downloader, and it supports SSL if we need it
        if not self.downloader or (
                (is_ssl and not self.downloader.supports_ssl())
                or (not is_ssl and not self.downloader.supports_plaintext())):

            for downloader_name in downloader_list:

                try:
                    downloader_class = DOWNLOADERS[downloader_name]
                    if downloader_class is None:
                        continue

                except KeyError:
                    error_string = text.format(
                        '''
                        The downloader "%s" from the "downloader_precedence"
                        setting for the platform "%s" is invalid
                        ''',
                        (downloader_name, platform)
                    )
                    show_error(error_string)
                    raise DownloaderException(error_string)

                try:
                    downloader = downloader_class(self.settings)
                    if is_ssl and not downloader.supports_ssl():
                        continue
                    if not is_ssl and not downloader.supports_plaintext():
                        continue
                    self.downloader = downloader
                    break

                except BinaryNotFoundError:
                    pass

        if not self.downloader:
            error_string = text.format(
                '''
                None of the preferred downloaders can download %s.

                This is usually either because the ssl module is unavailable
                and/or the command line curl or wget executables could not be
                found in the PATH.

                If you customized the "downloader_precedence" setting, please
                verify your customization.
                ''',
                url
            )
            show_error(error_string)
            raise DownloaderException(error_string.replace('\n\n', ' '))

        url = url.replace(' ', '%20')
        parsed = urlparse(url)
        if not parsed or not parsed.hostname:
            raise DownloaderException('The URL "%s" is malformed' % url)
        hostname = parsed.hostname.lower()

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
            except (socket.gaierror):
                ipv6 = None
            except (TypeError):
                ipv6 = None

            try:
                ip = socket.gethostbyname(hostname)
            except (socket.gaierror) as e:
                ip = str(e)
            except (TypeError):
                ip = None

            console_write(
                '''
                Download Debug
                  URL: %s
                  Timeout: %s
                  Resolved IP: %s
                ''',
                (url, str(timeout), ip)
            )
            if ipv6:
                console_write(
                    '  Resolved IPv6: %s',
                    ipv6,
                    prefix=False
                )

        if hostname in rate_limited_domains:
            exception = RateLimitSkipException(hostname)
            if self.settings.get('debug'):
                console_write('  %s' % exception, prefix=False)
            raise exception

        try:
            return self.downloader.download(url, error_message, timeout, 3, prefer_cached)

        except (RateLimitException) as e:
            rate_limited_domains.append(hostname)
            set_cache(
                'rate_limited_domains',
                rate_limited_domains,
                self.settings.get('cache_length', 604800)
            )

            console_write(
                '''
                %s Skipping all further download requests for this domain.
                ''',
                str(e)
            )
            raise

        except (OscryptoDownloaderException) as e:
            console_write(
                '''
                Attempting to use Urllib downloader due to Oscrypto error: %s
                ''',
                str(e)
            )

            self.downloader = UrlLibDownloader(self.settings)
            # Try again with the new downloader!
            return self.fetch(url, error_message, prefer_cached)

        except (WinDownloaderException) as e:
            console_write(
                '''
                Attempting to use Urllib downloader due to WinINet error: %s
                ''',
                str(e)
            )

            # Here we grab the proxy info extracted from WinInet to fill in
            # the Package Control settings if those are not present. This should
            # hopefully make a seamless fallback for users who run into weird
            # windows errors related to network communication.
            wininet_proxy = self.downloader.proxy or ''
            wininet_proxy_username = self.downloader.proxy_username or ''
            wininet_proxy_password = self.downloader.proxy_password or ''

            http_proxy = self.settings.get('http_proxy', '')
            https_proxy = self.settings.get('https_proxy', '')
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
