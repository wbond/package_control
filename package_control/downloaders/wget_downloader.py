import tempfile
import re
import os
import urlparse

from ..console_write import console_write
from ..unicode import unicode_from_os
from .cli_downloader import CliDownloader
from .non_http_error import NonHttpError
from .non_clean_exit_error import NonCleanExitError
from ..http.rate_limit_exception import RateLimitException


class WgetDownloader(CliDownloader):
    """
    A downloader that uses the command line program wget

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.settings = settings
        self.debug = settings.get('debug')
        self.wget = self.find_binary('wget')

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

        if not self.wget:
            return False

        self.tmp_file = tempfile.NamedTemporaryFile().name
        command = [self.wget, '--connect-timeout=' + str(int(timeout)), '-o',
            self.tmp_file, '-O', '-', '-U',
            self.settings.get('user_agent'), '--header',
            # Don't be alarmed if the response from the server does not select
            # one of these since the server runs a relatively new version of
            # OpenSSL which supports compression on the SSL layer, and Apache
            # will use that instead of HTTP-level encoding.
            'Accept-Encoding: gzip,deflate']

        secure_url_match = re.match('^https://([^/]+)', url)
        if secure_url_match != None:
            secure_domain = secure_url_match.group(1)
            bundle_path = self.check_certs(secure_domain, timeout)
            if not bundle_path:
                return False
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

        extra_options = self.settings.get('extra_wget_options')
        if extra_options:
            command.extend(extra_options)

        command.append(url)

        if http_proxy:
            os.putenv('http_proxy', http_proxy)
        if https_proxy:
            os.putenv('https_proxy', https_proxy)

        while tries > 0:
            tries -= 1
            try:
                result = self.execute(command)

                general, headers = self.parse_output()
                encoding = headers.get('content-encoding')
                if encoding:
                    result = self.decode_response(encoding, result)

                return result

            except (NonCleanExitError) as (e):

                try:
                    general, headers = self.parse_output()
                    self.handle_rate_limit(headers, url)

                    if general['status'] == '503':
                        # GitHub and BitBucket seem to rate limit via 503
                        error_string = u'Downloading %s was rate limited, trying again' % url
                        console_write(error_string, True)
                        continue

                    download_error = 'HTTP error %s %s' % (general['status'],
                        general['message'])

                except (NonHttpError) as (e):

                    download_error = unicode(e)

                    # GitHub and BitBucket seem to time out a lot
                    if download_error.find('timed out') != -1:
                        error_string = u'Downloading %s timed out, trying again' % url
                        console_write(error_string, True)
                        continue

                error_string = u'%s %s downloading %s.' % (error_message, download_error, url)
                console_write(error_string, True)

            break
        return False

    def parse_output(self):
        with open(self.tmp_file, 'r') as f:
            output = unicode_from_os(f.read()).splitlines()
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
        if not output:
            with open(self.tmp_file, 'r') as f:
                output = f.read().splitlines()
            self.clean_tmp_file()

        general = {
            'version': '0.9',
            'status':  '200',
            'message': 'OK'
        }
        headers = {}
        for line in output:
            # When using the -S option, headers have two spaces before them,
            # additionally, valid headers won't have spaces, so this is always
            # a safe operation to perform
            line = line.lstrip()
            if line.find('HTTP/') == 0:
                match = re.match('HTTP/(\d\.\d)\s+(\d+)\s+(.*)$', line)
                general['version'] = match.group(1)
                general['status'] = match.group(2)
                general['message'] = match.group(3)
            else:
                name, value = line.split(':', 1)
                headers[name.lower()] = value.strip()

        return (general, headers)

    def handle_rate_limit(self, headers, url):
        limit_remaining = headers.get('x-ratelimit-remaining', '1')
        limit = headers.get('x-ratelimit-limit', '1')

        if str(limit_remaining) == '0':
            hostname = urlparse.urlparse(url).hostname
            raise RateLimitException(hostname, limit)
