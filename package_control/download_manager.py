from __future__ import annotations
import asyncio
import os
import re
import sqlite3
import ssl
import time

from pathlib import Path
from threading import Lock, Timer
from typing import TYPE_CHECKING
from urllib.parse import unquote_to_bytes, urljoin

from .console_write import console_write
from .sys_path import pc_cache_dir
from .vendor import anysqlite
from .vendor import httpx
from .vendor import hishel
from .vendor.httpx import HTTPStatusError, Request, RequestError, Response

if TYPE_CHECKING:
    from typing import Generator

_client = None
"""Active HTTP client in use"""

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
          - ``http_basic_auth``
          - ``http_cache``
          - ``http_cache_length``
          - ``http_proxy``
          - ``proxy_ca``
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

    if url[:8].lower() == "file:///":
        try:
            with open(from_uri(url), "rb") as f:
                return f.read()
        except OSError as e:
            raise DownloaderException(str(e))

    global _client, _in_use, _timer

    try:
        with _lock:
            if _timer:
                _timer.cancel()
                _timer = None

            if _client is None:
                _client = create_client(settings)

            _in_use += 1

        response = _client.get(update_url(url, False))
        if response.is_error:
            raise DownloaderException(f"HTTP Errror {response.status_code} for {response.url}")

        return response.content

    finally:
        with _lock:
            _in_use -= 1
            if _in_use < 1:
                if _timer:
                    _timer.cancel()
                _timer = Timer(20.0, close_client)
                _timer.start()


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


def create_client(settings):
    """
    Creates a HTTP client.

    :param settings:
        A dictionary with settings

    :returns:
        httpx.Client object
    """
    # setup http(s) proxy
    proxy = None
    proxy_url = settings.get("http_proxy")
    if proxy_url:
        proxy_url = httpx.URL(os.path.expandvars(proxy_url))

        # setup ssl context
        proxy_ssl_context = None
        if proxy_url.scheme == "https":
            proxy_cafile = settings.get("proxy_cafile")
            if proxy_cafile:
                proxy_ssl_context = ssl.create_default_context(cafile=os.path.expandvars(proxy_cafile))

        # setup authentication
        proxy_auth = None
        proxy_user = settings.get("proxy_username")
        if proxy_user:
            proxy_auth = (
                os.path.expandvars(proxy_user),
                os.path.expandvars(settings.get("proxy_password", ""))
            )

        # instantiate proxy
        proxy = httpx.Proxy(
            url=proxy_url,
            auth=proxy_auth,
            ssl_context=proxy_ssl_context
        )

    return httpx.Client(
        auth=HostSpecificBasicAuth(settings.get("http_basic_auth")),
        headers={
            "user-agent": settings["user_agent"]
        },
        transport=hishel.CacheTransport(
            transport=RateLimitTransport(
                transport=httpx.HTTPTransport(
                    http2=True,
                    proxy=proxy
                ),
            ),
            controller=hishel.Controller(
                allow_heuristics=True,
                allow_stale=True,
            ),
            storage=hishel.SQLiteStorage(
                connection=cache_db(),
                ttl=settings.get("http_cache_length", 604800)
            )
        ),
        follow_redirects=True,
    )


def close_client():
    global _client

    with _lock:
        if _client:
            _client.close()
            _client = None


def cache_db():
    cache_dir = Path(pc_cache_dir())
    cache_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(cache_dir / "http_cache.sqlite", check_same_thread=False)
    connection.execute("PRAGMA analysis_limit = 400")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA journal_size_limit = 27103364")
    connection.execute("PRAGMA legacy_alter_table = OFF")
    connection.execute("PRAGMA mmap_size = 134217728")
    connection.execute("PRAGMA optimize")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA temp_store = memory")
    return connection


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


class DownloaderException(Exception):
    """If a downloader could not download a URL"""


class RateLimitException(DownloaderException):
    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, domain, limit):
        self.domain = domain
        self.limit = limit

    def __str__(self):
        return f"Hit rate limit of {self.limit} for {self.domain}."


class RateLimitSkipException(DownloaderException):
    """
    An exception for when skipping requests due to rate limit of an API has been exceeded.
    """

    def __init__(self, domain):
        self.domain = domain

    def __str__(self):
        return f"Skipping {self.domain} due to rate limit."


class HostSpecificBasicAuth(httpx.Auth):
    """
    Allows the 'auth' argument to be passed as a (username, password) pair,
    and uses HTTP Basic authentication.
    """

    def __init__(self, auth: dict[str, tuple[str, str]]) -> None:
        self._auth = {
            host: httpx.BasicAuth(*map(os.path.expandvars, user_password))
            for host, user_password in auth.items()
        }

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        if request.url.host in self._auth:
            yield from self._auth[request.url.host].auth_flow(request)
        else:
            yield request


class RateLimitTransport(httpx.BaseTransport):
    """
    This class describes a rate limit transport with legacy behaviror.

    The transport behaves like Package Control's legacy rate_limiting_downloader
    by just raising `RateLimitException` exception if a domain's rate limit
    has been exceeted, skipping all further requests by `RateLimitSkipException`.
    """
    def __init__(self, *args, transport: httpx.BaseTransport, **kwargs):
        super().__init__(*args, **kwargs)
        self._transport = transport
        self._rate_limits = {}

    def handle_request(self, request: Request) -> Response:
        # skip furhter requests to rate limited host
        if request.url.host in self._rate_limits:
            if self._rate_limits[request.url.host] > int(time.time()):
                raise RateLimitSkipException(request.url.host)

            del self._rate_limits[request.url.host]

        response = self._transport.handle_request(request)
        if response.status_code == 403:
            limit_remaining = int(response.headers.get('x-ratelimit-remaining', '1'))
            if limit_remaining == 0:
                limit = int(response.headers.get('x-ratelimit-limit', '1'))
                self._rate_limits[request.url.host] = int(response.headers.get('x-ratelimit-reset', '1'))
                raise RateLimitException(response.url.host, limit)

        return response
