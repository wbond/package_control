try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

import tempfile
import re
import os

from ..console_write import console_write
from .cli_downloader import CliDownloader
from .non_clean_exit_error import NonCleanExitError
from ..http.rate_limit_exception import RateLimitException
from ..open_compat import open_compat, read_compat


class CurlDownloader(CliDownloader):
    """
    A downloader that uses the command line program curl

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.settings = settings
        self.curl = self.find_binary('curl')

    def download(self, url, error_message, timeout, tries):
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

        :return:
            The string contents of the URL, or False on error
        """

        if not self.curl:
            return False

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

        secure_url_match = re.match('^https://([^/]+)', url)
        if secure_url_match != None:
            secure_domain = secure_url_match.group(1)
            bundle_path = self.check_certs(secure_domain, timeout)
            if not bundle_path:
                return False
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

        while tries > 0:
            tries -= 1
            try:
                output = self.execute(command)

                with open_compat(self.tmp_file, 'r') as f:
                    headers = read_compat(f)
                self.clean_tmp_file()

                limit = 1
                limit_remaining = 1
                status = '200 OK'
                for header in headers.splitlines():
                    if header[0:5] == 'HTTP/':
                        status = re.sub('^HTTP/\d\.\d\s+', '', header)
                    if header.lower()[0:22] == 'x-ratelimit-remaining:':
                        limit_remaining = header.lower()[22:].strip()
                    if header.lower()[0:18] == 'x-ratelimit-limit:':
                        limit = header.lower()[18:].strip()

                if debug:
                    self.print_debug(self.stderr.decode('utf-8'))

                if str(limit_remaining) == '0':
                    hostname = urlparse(url).hostname
                    raise RateLimitException(hostname, limit)

                if status != '200 OK':
                    e = NonCleanExitError(22)
                    e.stderr = status
                    raise e

                return output

            except (NonCleanExitError) as e:
                # Stderr is used for both the error message and the debug info
                # so we need to process it to extra the debug info
                if self.settings.get('debug'):
                    e.stderr = self.print_debug(e.stderr.decode('utf-8'))

                self.clean_tmp_file()

                if e.returncode == 22:
                    code = re.sub('^.*?(\d+)([\w\s]+)?$', '\\1', e.stderr)
                    if code == '503':
                        # GitHub and BitBucket seem to rate limit via 503
                        error_string = u'Downloading %s was rate limited, trying again' % url
                        console_write(error_string, True)
                        continue

                    download_error = u'HTTP error ' + code

                elif e.returncode == 6:
                    download_error = u'URL error host not found'

                elif e.returncode == 28:
                    # GitHub and BitBucket seem to time out a lot
                    error_string = u'Downloading %s timed out, trying again' % url
                    console_write(error_string, True)
                    continue

                else:
                    download_error = e.stderr.rstrip()

                error_string = u'%s %s downloading %s.' % (error_message, download_error, url)
                console_write(error_string, True)

            break

        return False

    def print_debug(self, string):
        section = 'General'
        last_section = None

        output = ''

        for line in string.splitlines():
            # Placeholder for body of request
            if line and line[0:2] == '{ ':
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
                    output += line
                    continue

            if line.strip() == '':
                continue

            if section != last_section:
                console_write(u"Curl HTTP Debug %s" % section, True)

            console_write(u'  ' + line)
            last_section = section

        return output
