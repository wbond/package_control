import re
import os
import sys

from .. import http

try:
    # Python 3
    from http.client import HTTPException, BadStatusLine
    from urllib.request import ProxyHandler, HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler, ProxyDigestAuthHandler, build_opener, Request
    from urllib.error import HTTPError, URLError
    import urllib.request as urllib_compat
except (ImportError):
    # Python 2
    from httplib import HTTPException, BadStatusLine
    from urllib2 import ProxyHandler, HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler, ProxyDigestAuthHandler, build_opener, Request
    from urllib2 import HTTPError, URLError
    import urllib2 as urllib_compat

try:
    # Python 3.3
    import ConnectionError
except (ImportError):
    # Python 2.6-3.2
    from socket import error as ConnectionError

from ..console_write import console_write
from ..unicode import unicode_from_os
from ..http.validating_https_handler import ValidatingHTTPSHandler
from ..http.debuggable_http_handler import DebuggableHTTPHandler
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from ..ca_certs import get_ca_bundle_path
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class UrlLibDownloader(DecodingDownloader, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the Python urllib module

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.opener = None
        self.settings = settings

    def close(self):
        """
        Closes any persistent/open connections
        """

        if not self.opener:
            return
        handler = self.get_handler()
        if handler:
            handler.close()
        self.opener = None

    def download(self, url, error_message, timeout, tries, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        Uses the proxy settings from the Package Control.sublime-settings file,
        however there seem to be a decent number of proxies that this code
        does not work with. Patches welcome!

        :param url:
            The URL to download

        :param error_message:
            A string to include in the console error that is printed
            when an error occurs

        :param timeout:
            The int number of seconds to set the timeout to

        :param tries:
            The int number of times to try and download the URL in the case of
            a timeout or HTTP 503 error

        :param prefer_cached:
            If a cached version should be returned instead of trying a new request

        :raises:
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        self.setup_opener(url, timeout)

        debug = self.settings.get('debug')
        error_string = None
        while tries > 0:
            tries -= 1
            try:
                request_headers = {
                    # Don't be alarmed if the response from the server does not
                    # select one of these since the server runs a relatively new
                    # version of OpenSSL which supports compression on the SSL
                    # layer, and Apache will use that instead of HTTP-level
                    # encoding.
                    "Accept-Encoding": self.supported_encodings()
                }
                user_agent = self.settings.get('user_agent')
                if user_agent:
                    request_headers["User-Agent"] = user_agent

                request_headers = self.add_conditional_headers(url, request_headers)
                request = Request(url, headers=request_headers)
                http_file = self.opener.open(request, timeout=timeout)
                self.handle_rate_limit(http_file.headers, url)

                result = http_file.read()
                # Make sure the response is closed so we can re-use the connection
                http_file.close()

                encoding = http_file.headers.get('content-encoding')
                result = self.decode_response(encoding, result)

                return self.cache_result('get', url, http_file.getcode(),
                    http_file.headers, result)

            except (HTTPException) as e:
                # Since we use keep-alives, it is possible the other end closed
                # the connection, and we may just need to re-open
                if isinstance(e, BadStatusLine):
                    handler = self.get_handler()
                    if handler and handler.use_count > 1:
                        self.close()
                        self.setup_opener(url, timeout)
                        tries += 1
                        continue

                error_string = u'%s HTTP exception %s (%s) downloading %s.' % (
                    error_message, e.__class__.__name__, unicode_from_os(e), url)

            except (HTTPError) as e:
                # Make sure the response is closed so we can re-use the connection
                e.read()
                e.close()

                # Make sure we obey Github's rate limiting headers
                self.handle_rate_limit(e.headers, url)

                # Handle cached responses
                if unicode_from_os(e.code) == '304':
                    return self.cache_result('get', url, int(e.code), e.headers, b'')

                # Bitbucket and Github return 503 a decent amount
                if unicode_from_os(e.code) == '503' and tries != 0:
                    error_string = u'Downloading %s was rate limited' % url
                    if tries:
                        error_string += ', trying again'
                        if debug:
                            console_write(error_string, True)
                    continue

                error_string = u'%s HTTP error %s downloading %s.' % (
                    error_message, unicode_from_os(e.code), url)

            except (URLError) as e:

                # Bitbucket and Github timeout a decent amount
                if unicode_from_os(e.reason) == 'The read operation timed out' \
                        or unicode_from_os(e.reason) == 'timed out':
                    error_string = u'Downloading %s timed out' % url
                    if tries:
                        error_string += ', trying again'
                        if debug:
                            console_write(error_string, True)
                    continue

                error_string = u'%s URL error %s downloading %s.' % (
                    error_message, unicode_from_os(e.reason), url)

            except (ConnectionError):
                # Handle broken pipes/reset connections by creating a new opener, and
                # thus getting new handlers and a new connection
                error_string = u'Connection went away while trying to download %s, trying again' % url
                if debug:
                    console_write(error_string, True)

                self.opener = None
                self.setup_opener(url, timeout)

                continue

            break

        raise DownloaderException(error_string)

    def get_handler(self):
        """
        Get the HTTPHandler object for the current connection
        """

        if not self.opener:
            return None

        for handler in self.opener.handlers:
            if isinstance(handler, ValidatingHTTPSHandler) or isinstance(handler, DebuggableHTTPHandler):
                return handler

    def setup_opener(self, url, timeout):
        """
        Sets up a urllib OpenerDirector to be used for requests. There is a
        fair amount of custom urllib code in Package Control, and part of it
        is to handle proxies and keep-alives. Creating an opener the way
        below is because the handlers have been customized to send the
        "Connection: Keep-Alive" header and hold onto connections so they
        can be re-used.

        :param url:
            The URL to download

        :param timeout:
            The int number of seconds to set the timeout to
        """

        if not self.opener:
            http_proxy = self.settings.get('http_proxy')
            https_proxy = self.settings.get('https_proxy')
            if http_proxy or https_proxy:
                proxies = {}
                if http_proxy:
                    proxies['http'] = http_proxy
                if https_proxy:
                    proxies['https'] = https_proxy
                proxy_handler = ProxyHandler(proxies)
            else:
                proxy_handler = ProxyHandler()

            password_manager = HTTPPasswordMgrWithDefaultRealm()
            proxy_username = self.settings.get('proxy_username')
            proxy_password = self.settings.get('proxy_password')
            if proxy_username and proxy_password:
                if http_proxy:
                    password_manager.add_password(None, http_proxy, proxy_username,
                        proxy_password)
                if https_proxy:
                    password_manager.add_password(None, https_proxy, proxy_username,
                        proxy_password)

            handlers = [proxy_handler]

            basic_auth_handler = ProxyBasicAuthHandler(password_manager)
            digest_auth_handler = ProxyDigestAuthHandler(password_manager)
            handlers.extend([digest_auth_handler, basic_auth_handler])

            debug = self.settings.get('debug')

            if debug:
                console_write(u"Urllib Debug Proxy", True)
                console_write(u"  http_proxy: %s" % http_proxy)
                console_write(u"  https_proxy: %s" % https_proxy)
                console_write(u"  proxy_username: %s" % proxy_username)
                console_write(u"  proxy_password: %s" % proxy_password)

            secure_url_match = re.match('^https://([^/]+)', url)
            if secure_url_match != None:
                secure_domain = secure_url_match.group(1)
                bundle_path = get_ca_bundle_path(self.settings)
                bundle_path = bundle_path.encode(sys.getfilesystemencoding())
                handlers.append(ValidatingHTTPSHandler(ca_certs=bundle_path,
                    debug=debug, passwd=password_manager,
                    user_agent=self.settings.get('user_agent')))
            else:
                handlers.append(DebuggableHTTPHandler(debug=debug,
                    passwd=password_manager))
            self.opener = build_opener(*handlers)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """
        return 'ssl' in sys.modules and hasattr(urllib_compat, 'HTTPSHandler')
