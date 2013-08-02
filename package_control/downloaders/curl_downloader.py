import tempfile
import re
import os

from ..console_write import console_write
from ..open_compat import open_compat, read_compat
from .cli_downloader import CliDownloader
from .non_clean_exit_error import NonCleanExitError
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .cert_provider import CertProvider
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class CurlDownloader(CliDownloader, CertProvider, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the command line program curl

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.

    :raises:
        BinaryNotFoundError: when curl can not be found
    """

    def __init__(self, settings):
        self.settings = settings
        self.curl = self.find_binary('curl')

    def close(self):
        """
        No-op for compatibility with UrllibDownloader and WinINetDownloader
        """

        pass

    def download(self, url, error_message, timeout, tries, prefer_cached=False):
        """
        Downloads a URL and returns the contents

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
            NoCaCertException: when no CA certs can be found for the url
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        self.tmp_file = tempfile.NamedTemporaryFile().name
        command = [self.curl, '--user-agent', self.settings.get('user_agent'),
            '--connect-timeout', str(int(timeout)), '-sSL',
            # Don't be alarmed if the response from the server does not select
            # one of these since the server runs a relatively new version of
            # OpenSSL which supports compression on the SSL layer, and Apache
            # will use that instead of HTTP-level encoding.
            '--compressed',
            # We have to capture the headers to check for rate limit info
            '--dump-header', self.tmp_file]

        request_headers = self.add_conditional_headers(url, {})

        for name, value in request_headers.items():
            command.extend(['--header', "%s: %s" % (name, value)])

        secure_url_match = re.match('^https://([^/]+)', url)
        if secure_url_match != None:
            secure_domain = secure_url_match.group(1)
            bundle_path = self.check_certs(secure_domain, timeout)
            command.extend(['--cacert', bundle_path])

        debug = self.settings.get('debug')
        if debug:
            command.append('-v')

        http_proxy = self.settings.get('http_proxy')
        https_proxy = self.settings.get('https_proxy')
        proxy_username = self.settings.get('proxy_username')
        proxy_password = self.settings.get('proxy_password')

        if debug:
            console_write(u"Curl Debug Proxy", True)
            console_write(u"  http_proxy: %s" % http_proxy)
            console_write(u"  https_proxy: %s" % https_proxy)
            console_write(u"  proxy_username: %s" % proxy_username)
            console_write(u"  proxy_password: %s" % proxy_password)

        if http_proxy or https_proxy:
            command.append('--proxy-anyauth')

        if proxy_username or proxy_password:
            command.extend(['-U', u"%s:%s" % (proxy_username, proxy_password)])

        if http_proxy:
            os.putenv('http_proxy', http_proxy)
        if https_proxy:
            os.putenv('HTTPS_PROXY', https_proxy)

        command.append(url)

        error_string = None
        while tries > 0:
            tries -= 1
            try:
                output = self.execute(command)

                with open_compat(self.tmp_file, 'r') as f:
                    headers_str = read_compat(f)
                self.clean_tmp_file()

                message = 'OK'
                status = 200
                headers = {}
                for header in headers_str.splitlines():
                    if header[0:5] == 'HTTP/':
                        message = re.sub('^HTTP/\d\.\d\s+\d+\s*', '', header)
                        status = int(re.sub('^HTTP/\d\.\d\s+(\d+)(\s+.*)?$', '\\1', header))
                        continue
                    if header.strip() == '':
                        continue
                    name, value = header.split(':', 1)
                    headers[name.lower()] = value.strip()

                if debug:
                    self.print_debug(self.stderr.decode('utf-8'))

                self.handle_rate_limit(headers, url)

                if status not in [200, 304]:
                    e = NonCleanExitError(22)
                    e.stderr = "%s %s" % (status, message)
                    raise e

                output = self.cache_result('get', url, status, headers, output)

                return output

            except (NonCleanExitError) as e:
                # Stderr is used for both the error message and the debug info
                # so we need to process it to extra the debug info
                if self.settings.get('debug'):
                    if hasattr(e.stderr, 'decode'):
                        e.stderr = e.stderr.decode('utf-8')
                    e.stderr = self.print_debug(e.stderr)

                self.clean_tmp_file()

                if e.returncode == 22:
                    code = re.sub('^.*?(\d+)([\w\s]+)?$', '\\1', e.stderr)
                    if code == '503' and tries != 0:
                        # GitHub and BitBucket seem to rate limit via 503
                        error_string = u'Downloading %s was rate limited' % url
                        if tries:
                            error_string += ', trying again'
                            if debug:
                                console_write(error_string, True)
                        continue

                    download_error = u'HTTP error ' + code

                elif e.returncode == 6:
                    download_error = u'URL error host not found'

                elif e.returncode == 28:
                    # GitHub and BitBucket seem to time out a lot
                    error_string = u'Downloading %s timed out' % url
                    if tries:
                        error_string += ', trying again'
                        if debug:
                            console_write(error_string, True)
                    continue

                else:
                    download_error = e.stderr.rstrip()

                error_string = u'%s %s downloading %s.' % (error_message, download_error, url)

            break

        raise DownloaderException(error_string)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """

        return True

    def print_debug(self, string):
        """
        Takes debug output from curl and groups and prints it

        :param string:
            The complete debug output from curl

        :return:
            A string containing any stderr output
        """

        section = 'General'
        last_section = None

        output = ''

        for line in string.splitlines():
            # Placeholder for body of request
            if line and line[0:2] == '{ ':
                continue
            if line and line[0:18] == '} [data not shown]':
                continue

            if len(line) > 1:
                subtract = 0
                if line[0:2] == '* ':
                    section = 'General'
                    subtract = 2
                elif line[0:2] == '> ':
                    section = 'Write'
                    subtract = 2
                elif line[0:2] == '< ':
                    section = 'Read'
                    subtract = 2
                line = line[subtract:]

                # If the line does not start with "* ", "< ", "> " or "  "
                # then it is a real stderr message
                if subtract == 0 and line[0:2] != '  ':
                    output += line.rstrip() + ' '
                    continue

            if line.strip() == '':
                continue

            if section != last_section:
                console_write(u"Curl HTTP Debug %s" % section, True)

            console_write(u'  ' + line)
            last_section = section

        return output.rstrip()
