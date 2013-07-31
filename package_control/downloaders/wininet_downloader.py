from ctypes import windll, wintypes
import ctypes
import time
import re
import datetime
import struct
import locale

wininet = windll.wininet

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

from ..console_write import console_write
from ..unicode import unicode_from_os
from .non_http_error import NonHttpError
from .http_error import HttpError
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class WinINetDownloader(DecodingDownloader, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the Windows WinINet DLL to perform downloads. This
    has the benefit of utilizing system-level proxy configuration and CA certs.

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    # General constants
    ERROR_INSUFFICIENT_BUFFER = 122

    # InternetOpen constants
    INTERNET_OPEN_TYPE_PRECONFIG = 0

    # InternetConnect constants
    INTERNET_SERVICE_HTTP = 3
    INTERNET_FLAG_EXISTING_CONNECT = 0x20000000
    INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS = 0x00004000

    # InternetSetOption constants
    INTERNET_OPTION_CONNECT_TIMEOUT = 2
    INTERNET_OPTION_SEND_TIMEOUT = 5
    INTERNET_OPTION_RECEIVE_TIMEOUT = 6

    # InternetQueryOption constants
    INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
    INTERNET_OPTION_PROXY = 38
    INTERNET_OPTION_PROXY_USERNAME = 43
    INTERNET_OPTION_PROXY_PASSWORD = 44
    INTERNET_OPTION_CONNECTED_STATE = 50

    # HttpOpenRequest constants
    INTERNET_FLAG_KEEP_CONNECTION = 0x00400000
    INTERNET_FLAG_RELOAD = 0x80000000
    INTERNET_FLAG_NO_CACHE_WRITE = 0x04000000
    INTERNET_FLAG_PRAGMA_NOCACHE = 0x00000100
    INTERNET_FLAG_SECURE = 0x00800000

    # HttpQueryInfo constants
    HTTP_QUERY_RAW_HEADERS_CRLF = 22

    # InternetConnectedState constants
    INTERNET_STATE_CONNECTED = 1
    INTERNET_STATE_DISCONNECTED = 2
    INTERNET_STATE_DISCONNECTED_BY_USER = 0x10
    INTERNET_STATE_IDLE = 0x100
    INTERNET_STATE_BUSY = 0x200


    def __init__(self, settings):
        self.settings = settings
        self.debug = settings.get('debug')
        self.network_connection = None
        self.tcp_connection = None
        self.use_count = 0
        self.hostname = None
        self.port = None
        self.scheme = None
        self.was_offline = None

    def close(self):
        """
        Closes any persistent/open connections
        """

        closed = False
        changed_state_back = False

        if self.tcp_connection:
            wininet.InternetCloseHandle(self.tcp_connection)
            self.tcp_connection = None
            closed = True

        if self.network_connection:
            wininet.InternetCloseHandle(self.network_connection)
            self.network_connection = None
            closed = True

        if self.was_offline:
            dw_connected_state = wintypes.DWORD(self.INTERNET_STATE_DISCONNECTED_BY_USER)
            dw_flags = wintypes.DWORD(0)
            connected_info = InternetConnectedInfo(dw_connected_state, dw_flags)
            wininet.InternetSetOptionA(None,
                self.INTERNET_OPTION_CONNECTED_STATE, ctypes.byref(connected_info), ctypes.sizeof(connected_info))
            changed_state_back = True

        if self.debug:
            s = '' if self.use_count == 1 else 's'
            console_write(u"WinINet %s Debug General" % self.scheme.upper(), True)
            console_write(u"  Closing connection to %s on port %s after %s request%s" % (
                self.hostname, self.port, self.use_count, s))
            if changed_state_back:
                console_write(u"  Changed Internet Explorer back to Work Offline")

        self.hostname = None
        self.port = None
        self.scheme = None
        self.use_count = 0
        self.was_offline = None

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
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        url_info = urlparse(url)

        if not url_info.port:
            port = 443 if url_info.scheme == 'https' else 80
            hostname = url_info.netloc
        else:
            port = url_info.port
            hostname = url_info.hostname

        path = url_info.path
        if url_info.params:
            path += ';' + url_info.params
        if url_info.query:
            path += '?' + url_info.query

        request_headers = {
            'Accept-Encoding': 'gzip,deflate'
        }
        request_headers = self.add_conditional_headers(url, request_headers)

        created_connection = False
        # If we switched Internet Explorer out of "Work Offline" mode
        changed_to_online = False

        # If the user is requesting a connection to another server, close the connection
        if (self.hostname and self.hostname != hostname) or (self.port and self.port != port):
            self.close()

        # Reset the error info to a known clean state
        ctypes.windll.kernel32.SetLastError(0)

        # Save the internet setup in the class for re-use
        if not self.tcp_connection:
            created_connection = True

            # Connect to the internet if necessary
            state = self.read_option(None, self.INTERNET_OPTION_CONNECTED_STATE)
            state = ord(state)
            if state & self.INTERNET_STATE_DISCONNECTED or state & self.INTERNET_STATE_DISCONNECTED_BY_USER:
                # Track the previous state so we can go back once complete
                self.was_offline = True

                dw_connected_state = wintypes.DWORD(self.INTERNET_STATE_CONNECTED)
                dw_flags = wintypes.DWORD(0)
                connected_info = InternetConnectedInfo(dw_connected_state, dw_flags)
                wininet.InternetSetOptionA(None,
                    self.INTERNET_OPTION_CONNECTED_STATE, ctypes.byref(connected_info), ctypes.sizeof(connected_info))
                changed_to_online = True

            self.network_connection = wininet.InternetOpenW(self.settings.get('user_agent'),
                self.INTERNET_OPEN_TYPE_PRECONFIG, None, None, 0)

            if not self.network_connection:
                error_string = u'%s %s during network phase of downloading %s.' % (error_message, self.extract_error(), url)
                raise DownloaderException(error_string)

            win_timeout = wintypes.DWORD(int(timeout) * 1000)
            # Apparently INTERNET_OPTION_CONNECT_TIMEOUT just doesn't work, leaving it in hoping they may fix in the future
            wininet.InternetSetOptionA(self.network_connection,
                self.INTERNET_OPTION_CONNECT_TIMEOUT, win_timeout, ctypes.sizeof(win_timeout))
            wininet.InternetSetOptionA(self.network_connection,
                self.INTERNET_OPTION_SEND_TIMEOUT, win_timeout, ctypes.sizeof(win_timeout))
            wininet.InternetSetOptionA(self.network_connection,
                self.INTERNET_OPTION_RECEIVE_TIMEOUT, win_timeout, ctypes.sizeof(win_timeout))

            # Don't allow HTTPS sites to redirect to HTTP sites
            tcp_flags  = self.INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
            # Try to re-use an existing connection to the server
            tcp_flags |= self.INTERNET_FLAG_EXISTING_CONNECT
            self.tcp_connection = wininet.InternetConnectW(self.network_connection,
                hostname, port, None, None, self.INTERNET_SERVICE_HTTP, tcp_flags, 0)

            if not self.tcp_connection:
                error_string = u'%s %s during connection phase of downloading %s.' % (error_message, self.extract_error(), url)
                raise DownloaderException(error_string)

            # Normally the proxy info would come from IE, but this allows storing it in
            # the Package Control settings file.
            proxy_username = self.settings.get('proxy_username')
            proxy_password = self.settings.get('proxy_password')
            if proxy_username and proxy_password:
                username = ctypes.c_wchar_p(proxy_username)
                password = ctypes.c_wchar_p(proxy_password)
                wininet.InternetSetOptionW(self.tcp_connection,
                    self.INTERNET_OPTION_PROXY_USERNAME, ctypes.cast(username, ctypes.c_void_p), len(proxy_username))
                wininet.InternetSetOptionW(self.tcp_connection,
                    self.INTERNET_OPTION_PROXY_PASSWORD, ctypes.cast(password, ctypes.c_void_p), len(proxy_password))

            self.hostname = hostname
            self.port = port
            self.scheme = url_info.scheme

        else:
            if self.debug:
                console_write(u"WinINet %s Debug General" % self.scheme.upper(), True)
                console_write(u"  Re-using connection to %s on port %s for request #%s" % (
                    self.hostname, self.port, self.use_count))

        error_string = None
        while tries > 0:
            tries -= 1
            try:
                http_connection = None

                # Keep-alive for better performance
                http_flags  = self.INTERNET_FLAG_KEEP_CONNECTION
                # Prevent caching/retrieving from cache
                http_flags |= self.INTERNET_FLAG_RELOAD
                http_flags |= self.INTERNET_FLAG_NO_CACHE_WRITE
                http_flags |= self.INTERNET_FLAG_PRAGMA_NOCACHE
                # Use SSL
                if self.scheme == 'https':
                    http_flags |= self.INTERNET_FLAG_SECURE

                http_connection = wininet.HttpOpenRequestW(self.tcp_connection, u'GET', path, u'HTTP/1.1', None, None, http_flags, 0)
                if not http_connection:
                    error_string = u'%s %s during HTTP connection phase of downloading %s.' % (error_message, self.extract_error(), url)
                    raise DownloaderException(error_string)

                request_header_lines = []
                for header, value in request_headers.items():
                    request_header_lines.append(u"%s: %s" % (header, value))
                request_header_lines = u"\r\n".join(request_header_lines)

                success = wininet.HttpSendRequestW(http_connection, request_header_lines, len(request_header_lines), None, 0)

                if not success:
                    error_string = u'%s %s during HTTP write phase of downloading %s.' % (error_message, self.extract_error(), url)
                    raise DownloaderException(error_string)

                # If we try to query before here, the proxy info will not be available to the first request
                if self.debug:
                    proxy_struct = self.read_option(self.network_connection, self.INTERNET_OPTION_PROXY)
                    proxy = ''
                    if proxy_struct.lpszProxy:
                        proxy = proxy_struct.lpszProxy.decode('cp1252')
                    proxy_bypass = ''
                    if proxy_struct.lpszProxyBypass:
                        proxy_bypass = proxy_struct.lpszProxyBypass.decode('cp1252')

                    proxy_username = self.read_option(self.tcp_connection, self.INTERNET_OPTION_PROXY_USERNAME)
                    proxy_password = self.read_option(self.tcp_connection, self.INTERNET_OPTION_PROXY_PASSWORD)

                    console_write(u"WinINet Debug Proxy", True)
                    console_write(u"  proxy: %s" % proxy)
                    console_write(u"  proxy bypass: %s" % proxy_bypass)
                    console_write(u"  proxy username: %s" % proxy_username)
                    console_write(u"  proxy password: %s" % proxy_password)

                self.use_count += 1

                if self.debug and created_connection:
                    if self.scheme == 'https':
                        cert_struct = self.read_option(http_connection, self.INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT)

                        if cert_struct.lpszIssuerInfo:
                            issuer_info = cert_struct.lpszIssuerInfo.decode('cp1252')
                            issuer_parts = issuer_info.split("\r\n")
                        else:
                            issuer_parts = ['No issuer info']

                        if cert_struct.lpszSubjectInfo:
                            subject_info = cert_struct.lpszSubjectInfo.decode('cp1252')
                            subject_parts = subject_info.split("\r\n")
                        else:
                            subject_parts = ["No subject info"]

                        common_name = subject_parts[-1]

                        if cert_struct.ftStart.dwLowDateTime != 0 and cert_struct.ftStart.dwHighDateTime != 0:
                            issue_date = self.convert_filetime_to_datetime(cert_struct.ftStart)
                            issue_date = issue_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                        else:
                            issue_date = u"No issue date"

                        if cert_struct.ftExpiry.dwLowDateTime != 0 and cert_struct.ftExpiry.dwHighDateTime != 0:
                            expiration_date = self.convert_filetime_to_datetime(cert_struct.ftExpiry)
                            expiration_date = expiration_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                        else:
                            expiration_date = u"No expiration date"

                        console_write(u"WinINet HTTPS Debug General", True)
                        if changed_to_online:
                            console_write(u"  Internet Explorer was set to Work Offline, temporarily going online")
                        console_write(u"  Server SSL Certificate:")
                        console_write(u"    subject: %s" % ", ".join(subject_parts))
                        console_write(u"    issuer: %s" % ", ".join(issuer_parts))
                        console_write(u"    common name: %s" % common_name)
                        console_write(u"    issue date: %s" % issue_date)
                        console_write(u"    expire date: %s" % expiration_date)

                    elif changed_to_online:
                        console_write(u"WinINet HTTP Debug General", True)
                        console_write(u"  Internet Explorer was set to Work Offline, temporarily going online")

                if self.debug:
                    console_write(u"WinINet %s Debug Write" % self.scheme.upper(), True)
                    # Add in some known headers that WinINet sends since we can't get the real list
                    console_write(u"  GET %s HTTP/1.1" % path)
                    for header, value in request_headers.items():
                        console_write(u"  %s: %s" % (header, value))
                    console_write(u"  User-Agent: %s" % self.settings.get('user_agent'))
                    console_write(u"  Host: %s" % hostname)
                    console_write(u"  Connection: Keep-Alive")
                    console_write(u"  Cache-Control: no-cache")

                header_buffer_size = 8192

                try_again = True
                while try_again:
                    try_again = False

                    to_read_was_read = wintypes.DWORD(header_buffer_size)
                    headers_buffer = ctypes.create_string_buffer(header_buffer_size)

                    success = wininet.HttpQueryInfoA(http_connection, self.HTTP_QUERY_RAW_HEADERS_CRLF, ctypes.byref(headers_buffer), ctypes.byref(to_read_was_read), None)
                    if not success:
                        if ctypes.GetLastError() != self.ERROR_INSUFFICIENT_BUFFER:
                            error_string = u'%s %s during header read phase of downloading %s.' % (error_message, self.extract_error(), url)
                            raise DownloaderException(error_string)
                        # The error was a buffer that was too small, so try again
                        header_buffer_size = to_read_was_read.value
                        try_again = True
                        continue

                    headers = b''
                    if to_read_was_read.value > 0:
                        headers += headers_buffer.raw[:to_read_was_read.value]
                    headers = headers.decode('iso-8859-1').rstrip("\r\n").split("\r\n")

                    if self.debug:
                        console_write(u"WinINet %s Debug Read" % self.scheme.upper(), True)
                        for header in headers:
                            console_write(u"  %s" % header)

                buffer_length = 65536
                output_buffer = ctypes.create_string_buffer(buffer_length)
                bytes_read = wintypes.DWORD()

                result = b''
                try_again = True
                while try_again:
                    try_again = False
                    wininet.InternetReadFile(http_connection, output_buffer, buffer_length, ctypes.byref(bytes_read))
                    if bytes_read.value > 0:
                        result += output_buffer.raw[:bytes_read.value]
                        try_again = True

                general, headers = self.parse_headers(headers)
                self.handle_rate_limit(headers, url)

                if general['status'] == 503 and tries != 0:
                    # GitHub and BitBucket seem to rate limit via 503
                    error_string = u'Downloading %s was rate limited' % url
                    if tries:
                        error_string += ', trying again'
                        if self.debug:
                            console_write(error_string, True)
                    continue

                encoding = headers.get('content-encoding')
                if encoding:
                    result = self.decode_response(encoding, result)

                result = self.cache_result('get', url, general['status'],
                    headers, result)

                if general['status'] not in [200, 304]:
                    raise HttpError("HTTP error %s" % general['status'], general['status'])

                return result

            except (NonHttpError, HttpError) as e:

                # GitHub and BitBucket seem to time out a lot
                if str(e).find('timed out') != -1:
                    error_string = u'Downloading %s timed out' % url
                    if tries:
                        error_string += ', trying again'
                        if self.debug:
                            console_write(error_string, True)
                    continue

                error_string = u'%s %s downloading %s.' % (error_message, e, url)

            finally:
                if http_connection:
                    wininet.InternetCloseHandle(http_connection)

            break

        raise DownloaderException(error_string)

    def convert_filetime_to_datetime(self, filetime):
        """
        Windows returns times as 64-bit unsigned longs that are the number
        of hundreds of nanoseconds since Jan 1 1601. This converts it to
        a datetime object.

        :param filetime:
            A FileTime struct object

        :return:
            A (UTC) datetime object
        """

        hundreds_nano_seconds = struct.unpack('>Q', struct.pack('>LL', filetime.dwHighDateTime, filetime.dwLowDateTime))[0]
        seconds_since_1601 = hundreds_nano_seconds / 10000000
        epoch_seconds = seconds_since_1601 - 11644473600 # Seconds from Jan 1 1601 to Jan 1 1970
        return datetime.datetime.fromtimestamp(epoch_seconds)

    def extract_error(self):
        """
        Retrieves and formats an error from WinINet

        :return:
            A string with a nice description of the error
        """

        error_num = ctypes.GetLastError()
        raw_error_string = ctypes.FormatError(error_num)

        error_string = unicode_from_os(raw_error_string)

        # Try to fill in some known errors
        if error_string == u"<no description>":
            error_lookup = {
                12007: u'host not found',
                12029: u'connection refused',
                12057: u'error checking for server certificate revocation',
                12169: u'invalid secure certificate',
                12157: u'secure channel error, server not providing SSL',
                12002: u'operation timed out'
            }
            if error_num in error_lookup:
                error_string = error_lookup[error_num]

        if error_string == u"<no description>":
            return u"(errno %s)" % error_num

        error_string = error_string[0].upper() + error_string[1:]
        return u"%s (errno %s)" % (error_string, error_num)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """

        return True

    def read_option(self, handle, option):
        """
        Reads information about the internet connection, which may be a string or struct

        :param handle:
            The handle to query for the info

        :param option:
            The (int) option to get

        :return:
            A string, or one of the InternetCertificateInfo or InternetProxyInfo structs
        """

        option_buffer_size = 8192
        try_again = True

        while try_again:
            try_again = False

            to_read_was_read = wintypes.DWORD(option_buffer_size)
            option_buffer = ctypes.create_string_buffer(option_buffer_size)
            ref = ctypes.byref(option_buffer)

            success = wininet.InternetQueryOptionA(handle, option, ref, ctypes.byref(to_read_was_read))
            if not success:
                if ctypes.GetLastError() != self.ERROR_INSUFFICIENT_BUFFER:
                    raise NonHttpError(self.extract_error())
                # The error was a buffer that was too small, so try again
                option_buffer_size = to_read_was_read.value
                try_again = True
                continue

            if option == self.INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT:
                length = min(len(option_buffer), ctypes.sizeof(InternetCertificateInfo))
                cert_info = InternetCertificateInfo()
                ctypes.memmove(ctypes.addressof(cert_info), option_buffer, length)
                return cert_info
            elif option == self.INTERNET_OPTION_PROXY:
                length = min(len(option_buffer), ctypes.sizeof(InternetProxyInfo))
                proxy_info = InternetProxyInfo()
                ctypes.memmove(ctypes.addressof(proxy_info), option_buffer, length)
                return proxy_info
            else:
                option = b''
                if to_read_was_read.value > 0:
                    option += option_buffer.raw[:to_read_was_read.value]
                return option.decode('cp1252').rstrip("\x00")

    def parse_headers(self, output):
        """
        Parses HTTP headers into two dict objects

        :param output:
            An array of header lines

        :return:
            A tuple of (general, headers) where general is a dict with the keys:
              `version` - HTTP version number (string)
              `status` - HTTP status code (integer)
              `message` - HTTP status message (string)
            And headers is a dict with the keys being lower-case version of the
            HTTP header names.
        """

        general = {
            'version': '0.9',
            'status':  200,
            'message': 'OK'
        }
        headers = {}
        for line in output:
            line = line.lstrip()
            if line.find('HTTP/') == 0:
                match = re.match('HTTP/(\d\.\d)\s+(\d+)\s+(.*)$', line)
                general['version'] = match.group(1)
                general['status'] = int(match.group(2))
                general['message'] = match.group(3)
            else:
                name, value = line.split(':', 1)
                headers[name.lower()] = value.strip()

        return (general, headers)


class FileTime(ctypes.Structure):
    """
    A Windows struct used by InternetCertificateInfo for certificate
    date information
    """

    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD)
    ]


class InternetCertificateInfo(ctypes.Structure):
    """
    A Windows struct used to store information about an SSL certificate
    """

    _fields_ = [
        ("ftExpiry", FileTime),
        ("ftStart", FileTime),
        ("lpszSubjectInfo", ctypes.c_char_p),
        ("lpszIssuerInfo", ctypes.c_char_p),
        ("lpszProtocolName", ctypes.c_char_p),
        ("lpszSignatureAlgName", ctypes.c_char_p),
        ("lpszEncryptionAlgName", ctypes.c_char_p),
        ("dwKeySize", wintypes.DWORD)
    ]


class InternetProxyInfo(ctypes.Structure):
    """
    A Windows struct usd to store information about the configured proxy server
    """

    _fields_ = [
        ("dwAccessType", wintypes.DWORD),
        ("lpszProxy", ctypes.c_char_p),
        ("lpszProxyBypass", ctypes.c_char_p)
    ]


class InternetConnectedInfo(ctypes.Structure):
    """
    A Windows struct usd to store information about the global internet connection state
    """

    _fields_ = [
        ("dwConnectedState", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD)
    ]
