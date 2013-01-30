try:
    # Python 3
    from http.client import HTTPException
    from urllib.parse import urlparse
    from urllib.request import ProxyHandler, HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler, ProxyDigestAuthHandler, install_opener, build_opener, Request, urlopen
    from urllib.error import HTTPError, URLError
except (ImportError):
    # Python 2
    from httplib import HTTPException
    from urlparse import urlparse
    from urllib2 import ProxyHandler, HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler, ProxyDigestAuthHandler, install_opener, build_opener, Request, urlopen
    from urllib2 import HTTPError, URLError

import re
import os
import sys

from ..console_write import console_write
from ..unicode import unicode_from_os
from .downloader import Downloader
from ..http.validating_https_handler import ValidatingHTTPSHandler
from ..http.debuggable_http_handler import DebuggableHTTPHandler
from ..http.rate_limit_exception import RateLimitException
from ..http.proxy_ntlm_auth_handler import ProxyNtlmAuthHandler


class UrlLib2Downloader(Downloader):
    """
    A downloader that uses the Python urllib module

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.settings = settings

    def download(self, url, error_message, timeout, tries):
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

        :return:
            The string contents of the URL, or False on error
        """

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
        if os.name == 'nt':
            ntlm_auth_handler = ProxyNtlmAuthHandler(password_manager)
            handlers.append(ntlm_auth_handler)

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
            bundle_path = self.check_certs(secure_domain, timeout)
            if not bundle_path:
                return False
            bundle_path = bundle_path.encode(sys.getfilesystemencoding())
            handlers.append(ValidatingHTTPSHandler(ca_certs=bundle_path,
                debug=debug, passwd=password_manager,
                user_agent=self.settings.get('user_agent')))
        else:
            handlers.append(DebuggableHTTPHandler(debug=debug,
                passwd=password_manager))
        install_opener(build_opener(*handlers))

        while tries > 0:
            tries -= 1
            try:
                request = Request(url, headers={
                    "User-Agent": self.settings.get('user_agent'),
                    # Don't be alarmed if the response from the server does not
                    # select one of these since the server runs a relatively new
                    # version of OpenSSL which supports compression on the SSL
                    # layer, and Apache will use that instead of HTTP-level
                    # encoding.
                    "Accept-Encoding": "gzip,deflate"})
                http_file = urlopen(request, timeout=timeout)
                self.handle_rate_limit(http_file, url)
                result = http_file.read()
                encoding = http_file.headers.get('Content-Encoding')
                return self.decode_response(encoding, result)

            except (HTTPException) as e:
                error_string = u'%s HTTP exception %s (%s) downloading %s.' % (
                    error_message, e.__class__.__name__, unicode_from_os(e), url)
                console_write(error_string, True)

            except (HTTPError) as e:
                # Make sure we obey Github's rate limiting headers
                self.handle_rate_limit(e, url)

                # Bitbucket and Github return 503 a decent amount
                if unicode_from_os(e.code) == '503':
                    error_string = u'Downloading %s was rate limited, trying again' % url
                    console_write(error_string, True)
                    continue

                error_string = u'%s HTTP error %s downloading %s.' % (
                    error_message, unicode_from_os(e.code), url)
                console_write(error_string, True)

            except (URLError) as e:

                # Bitbucket and Github timeout a decent amount
                if unicode_from_os(e.reason) == 'The read operation timed out' \
                        or unicode_from_os(e.reason) == 'timed out':
                    error_string = u'Downloading %s timed out, trying again' % url
                    console_write(error_string, True)
                    continue

                error_string = u'%s URL error %s downloading %s.' % (
                    error_message, unicode_from_os(e.reason), url)
                console_write(error_string, True)

            break
        return False

    def handle_rate_limit(self, response, url):
        """
        Checks the headers of a respone object to make sure we are obeying the
        rate limit

        :param response:
            The response object that has a headers dict

        :param url:
            The URL that was requested

        :raises:
            RateLimitException when the rate limit has been hit
        """

        limit_remaining = response.headers.get('X-RateLimit-Remaining', 1)
        if str(limit_remaining) == '0':
            hostname = urlparse(url).hostname
            limit = response.headers.get('X-RateLimit-Limit', 1)
            raise RateLimitException(hostname, limit)
