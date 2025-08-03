import os
import re
import socket
import sys
from threading import Lock, Timer
from urllib.parse import unquote_to_bytes, urljoin, urlparse

from . import __version__
from . import text
from .cache import set_cache, get_cache
from .console_write import console_write
from .show_error import show_error

from .downloaders import DOWNLOADERS
from .downloaders.binary_not_found_error import BinaryNotFoundError
from .downloaders.downloader_exception import DownloaderException
from .downloaders.rate_limit_exception import RateLimitException
from .downloaders.rate_limit_exception import RateLimitSkipException
from .http_cache import HttpCache

_http_cache = None

_managers = {}
"""A dict of domains - each points to a list of downloaders"""

_in_use = 0
"""How many managers are currently checked out"""

_lock = Lock()
"""Make sure connection management doesn't run into threading issues"""

_timer = None
"""A timer used to disconnect all managers after a period of no usage"""


def http_get(url, settings, error_message=''):
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

    :raises:
        DownloaderException: if there was an error downloading the URL

    :return:
        The string contents of the URL
    """

    if url[:8].lower() == "file:///":
        try:
            with open(from_uri(url), "rb") as f:
                return f.read()
        except OSError as e:
            raise DownloaderException(str(e))

    manager = None
    result = None

    try:
        manager = _grab(url, settings)
        result = manager.fetch(url, error_message)

    finally:
        if manager:
            _release(url, manager)

    return result


def from_uri(uri: str) -> str:  # roughly taken from Python 3.13
    """Return a new path from the given 'file' URI."""
    if not uri.lower().startswith('file:'):
        raise ValueError("URI does not start with 'file:': {uri!r}".format(uri=uri))
    path = os.fsdecode(unquote_to_bytes(uri))
    path = path[5:]
    if path[:3] == '///':
        # Remove empty authority
        path = path[2:]
    elif path[:12].lower() == '//localhost/':
        # Remove 'localhost' authority
        path = path[11:]
    if path[:3] == '///' or (path[:1] == '/' and path[2:3] in ':|'):
        # Remove slash before DOS device/UNC path
        path = path[1:]
        path = path[0].upper() + path[1:]
    if path[1:2] == '|':
        # Replace bar with colon in DOS drive
        path = path[:1] + ':' + path[2:]
    if not os.path.isabs(path):
        raise ValueError(
            "URI is not absolute: {uri!r}. Parsed so far: {path!r}"
            .format(uri=uri, path=path)
        )
    return path


def _grab(url, settings):
    global _http_cache, _managers, _lock, _in_use, _timer

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
            http_cache = None
            if settings.get('http_cache'):
                # first call defines http cache settings
                # It is safe to assume all calls share same settings.
                if not _http_cache:
                    _http_cache = HttpCache(settings.get('http_cache_length', 604800))
                http_cache = _http_cache

            _managers[hostname].append(DownloadManager(settings, http_cache))

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
    global _http_cache, _managers, _lock, _in_use, _timer

    with _lock:
        if _timer:
            _timer.cancel()
            _timer = None

        if _http_cache:
            _http_cache.prune()
            _http_cache = None

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

    scheme_match = re.match(r'^(file:/|https?:)//', root_url, re.I)

    for url in uris:
        if not url:
            continue
        if url.startswith('//'):
            if scheme_match is not None:
                url = scheme_match.group(1) + url
            else:
                url = 'https:' + url
        elif url.startswith('/'):
            # We don't allow absolute repositories
            continue
        elif url.startswith('./') or url.startswith('../'):
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

    if not url:
        return url

    if url.startswith('//'):
        scheme_match = re.match(r'^(file:/|https?:)//', root_url, re.I)
        if scheme_match is not None:
            return scheme_match.group(1) + url
        else:
            return 'https:' + url

    elif url.startswith('./') or url.startswith('../'):
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

    def __init__(self, settings, http_cache=None):
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

        # assign global http cache storage driver
        if http_cache:
            self.settings['cache'] = http_cache

            # specify maximum time a local cache is considdered fresh
            # currently uses values from 'cache_length' setting to keep in sync
            # with in-memory key-value cache layer.
            max_age = settings.get('cache_length')
            if max_age is not None and 0 <= max_age <= 24 * 60 * 60:
                self.settings['max_age'] = max_age

    def close(self):
        if self.downloader:
            self.downloader.close()
            self.downloader = None

    def fetch(self, url, error_message):
        """
        Downloads a URL and returns the contents

        :param url:
            The string URL to download

        :param error_message:
            The error message to include if the download fails

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
            return self.downloader.download(url, error_message, timeout, 3)

        except (RateLimitException) as e:
            # rate limits are normally reset after an hour
            # store rate limited domain for this time to avoid further requests
            rate_limited_domains.append(hostname)
            set_cache('rate_limited_domains', rate_limited_domains, 3610)

            console_write(
                '''
                %s Skipping all further download requests for this domain.
                ''',
                str(e)
            )
            raise
