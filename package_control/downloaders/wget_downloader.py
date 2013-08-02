import tempfile
import re
import os

from ..console_write import console_write
from ..unicode import unicode_from_os
from ..open_compat import open_compat, read_compat
from .cli_downloader import CliDownloader
from .non_http_error import NonHttpError
from .non_clean_exit_error import NonCleanExitError
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .cert_provider import CertProvider
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class WgetDownloader(CliDownloader, CertProvider, DecodingDownloader, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the command line program wget

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.

    :raises:
        BinaryNotFoundError: when wget can not be found
    """

    def __init__(self, settings):
        self.settings = settings
        self.debug = settings.get('debug')
        self.wget = self.find_binary('wget')

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
        command = [self.wget, '--connect-timeout=' + str(int(timeout)), '-o',
            self.tmp_file, '-O', '-', '-U', self.settings.get('user_agent')]

        request_headers = {
            # Don't be alarmed if the response from the server does not select
            # one of these since the server runs a relatively new version of
            # OpenSSL which supports compression on the SSL layer, and Apache
            # will use that instead of HTTP-level encoding.
            'Accept-Encoding': 'gzip,deflate'
        }
        request_headers = self.add_conditional_headers(url, request_headers)

        for name, value in request_headers.items():
            command.extend(['--header', "%s: %s" % (name, value)])

        secure_url_match = re.match('^https://([^/]+)', url)
        if secure_url_match != None:
            secure_domain = secure_url_match.group(1)
            bundle_path = self.check_certs(secure_domain, timeout)
            command.append(u'--ca-certificate=' + bundle_path)

        if self.debug:
            command.append('-d')
        else:
            command.append('-S')

        http_proxy = self.settings.get('http_proxy')
        https_proxy = self.settings.get('https_proxy')
        proxy_username = self.settings.get('proxy_username')
        proxy_password = self.settings.get('proxy_password')

        if proxy_username:
            command.append(u"--proxy-user=%s" % proxy_username)
        if proxy_password:
            command.append(u"--proxy-password=%s" % proxy_password)

        if self.debug:
            console_write(u"Wget Debug Proxy", True)
            console_write(u"  http_proxy: %s" % http_proxy)
            console_write(u"  https_proxy: %s" % https_proxy)
            console_write(u"  proxy_username: %s" % proxy_username)
            console_write(u"  proxy_password: %s" % proxy_password)

        command.append(url)

        if http_proxy:
            os.putenv('http_proxy', http_proxy)
        if https_proxy:
            os.putenv('https_proxy', https_proxy)

        error_string = None
        while tries > 0:
            tries -= 1
            try:
                result = self.execute(command)

                general, headers = self.parse_output()
                encoding = headers.get('content-encoding')
                if encoding:
                    result = self.decode_response(encoding, result)

                result = self.cache_result('get', url, general['status'],
                    headers, result)

                return result

            except (NonCleanExitError) as e:

                try:
                    general, headers = self.parse_output()
                    self.handle_rate_limit(headers, url)

                    if general['status'] == 304:
                        return self.cache_result('get', url, general['status'],
                            headers, None)

                    if general['status'] == 503 and tries != 0:
                        # GitHub and BitBucket seem to rate limit via 503
                        error_string = u'Downloading %s was rate limited' % url
                        if tries:
                            error_string += ', trying again'
                            if self.debug:
                                console_write(error_string, True)
                        continue

                    download_error = 'HTTP error %s' % general['status']

                except (NonHttpError) as e:

                    download_error = unicode_from_os(e)

                    # GitHub and BitBucket seem to time out a lot
                    if download_error.find('timed out') != -1:
                        error_string = u'Downloading %s timed out' % url
                        if tries:
                            error_string += ', trying again'
                            if self.debug:
                                console_write(error_string, True)
                        continue

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

    def parse_output(self):
        """
        Parses the wget output file, prints debug information and returns headers

        :return:
            A tuple of (general, headers) where general is a dict with the keys:
              `version` - HTTP version number (string)
              `status` - HTTP status code (integer)
              `message` - HTTP status message (string)
            And headers is a dict with the keys being lower-case version of the
            HTTP header names.
        """

        with open_compat(self.tmp_file, 'r') as f:
            output = read_compat(f).splitlines()
        self.clean_tmp_file()

        error = None
        header_lines = []
        if self.debug:
            section = 'General'
            last_section = None
            for line in output:
                if section == 'General':
                    if self.skippable_line(line):
                        continue

                # Skip blank lines
                if line.strip() == '':
                    continue

                # Error lines
                if line[0:5] == 'wget:':
                    error = line[5:].strip()
                if line[0:7] == 'failed:':
                    error = line[7:].strip()

                if line == '---request begin---':
                    section = 'Write'
                    continue
                elif line == '---request end---':
                    section = 'General'
                    continue
                elif line == '---response begin---':
                    section = 'Read'
                    continue
                elif line == '---response end---':
                    section = 'General'
                    continue

                if section != last_section:
                    console_write(u"Wget HTTP Debug %s" % section, True)

                if section == 'Read':
                    header_lines.append(line)

                console_write(u'  ' + line)
                last_section = section

        else:
            for line in output:
                if self.skippable_line(line):
                    continue

                # Check the resolving and connecting to lines for errors
                if re.match('(Resolving |Connecting to )', line):
                    failed_match = re.search(' failed: (.*)$', line)
                    if failed_match:
                        error = failed_match.group(1).strip()

                # Error lines
                if line[0:5] == 'wget:':
                    error = line[5:].strip()
                if line[0:7] == 'failed:':
                    error = line[7:].strip()

                if line[0:2] == '  ':
                    header_lines.append(line.lstrip())

        if error:
            raise NonHttpError(error)

        return self.parse_headers(header_lines)

    def skippable_line(self, line):
        """
        Determines if a debug line is skippable - usually because of extraneous
        or duplicate information.

        :param line:
            The debug line to check

        :return:
            True if the line is skippable, otherwise None
        """

        # Skip date lines
        if re.match('--\d{4}-\d{2}-\d{2}', line):
            return True
        if re.match('\d{4}-\d{2}-\d{2}', line):
            return True
        # Skip HTTP status code lines since we already have that info
        if re.match('\d{3} ', line):
            return True
        # Skip Saving to and progress lines
        if re.match('(Saving to:|\s*\d+K)', line):
            return True
        # Skip notice about ignoring body on HTTP error
        if re.match('Skipping \d+ byte', line):
            return True

    def parse_headers(self, output=None):
        """
        Parses HTTP headers into two dict objects

        :param output:
            An array of header lines, if None, loads from temp output file

        :return:
            A tuple of (general, headers) where general is a dict with the keys:
              `version` - HTTP version number (string)
              `status` - HTTP status code (integer)
              `message` - HTTP status message (string)
            And headers is a dict with the keys being lower-case version of the
            HTTP header names.
        """

        if not output:
            with open_compat(self.tmp_file, 'r') as f:
                output = read_compat(f).splitlines()
            self.clean_tmp_file()

        general = {
            'version': '0.9',
            'status':  200,
            'message': 'OK'
        }
        headers = {}
        for line in output:
            # When using the -S option, headers have two spaces before them,
            # additionally, valid headers won't have spaces, so this is always
            # a safe operation to perform
            line = line.lstrip()
            if line.find('HTTP/') == 0:
                match = re.match('HTTP/(\d\.\d)\s+(\d+)(?:\s+(.*))?$', line)
                general['version'] = match.group(1)
                general['status'] = int(match.group(2))
                general['message'] = match.group(3) or ''
            else:
                name, value = line.split(':', 1)
                headers[name.lower()] = value.strip()

        return (general, headers)
