# coding: utf-8

from __future__ import unicode_literals, division, absolute_import, print_function

import base64
import re
import sys
import os
import hashlib
import socket

if sys.version_info < (3,):
    from urlparse import urlparse

    from urllib2 import parse_keqv_list, parse_http_list
    str_cls = unicode  # noqa
    int_types = (int, long)  # noqa
else:
    from urllib.parse import urlparse
    from urllib.request import parse_keqv_list, parse_http_list
    str_cls = str
    int_types = int

from ..deps.oscrypto import tls
from ..deps.oscrypto import errors as oscrypto_errors
from ..deps.asn1crypto.util import OrderedDict
from ..deps.asn1crypto import pem, x509

from ..console_write import console_write
from ..unicode import unicode_from_os
from ..open_compat import open_compat, read_compat
from .downloader_exception import DownloaderException
from .oscrypto_downloader_exception import OscryptoDownloaderException
from ..ca_certs import get_ca_bundle_path, get_user_ca_bundle_path
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader
from .. import text


class OscryptoDownloader(DecodingDownloader, LimitingDownloader, CachingDownloader):

    """
    A downloader that uses the Python oscrypto.tls module

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.socket = None
        self.timeout = None
        self.url_info = None
        self.proxy_info = None
        self.using_proxy = False
        self.user_agent = None
        self.debug = False
        self.settings = settings

    def close(self):
        """
        Closes any persistent/open connections
        """

        if not self.socket:
            return
        self.socket.close()
        self.socket = None
        self.using_proxy = False

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

        reused = None

        debug = self.debug
        tried = tries
        error_string = None
        while tries > 0:
            tries -= 1
            try:
                if reused is None:
                    reused = self.setup_connection(url, timeout)
                else:
                    self.ensure_connected()

                req_headers = OrderedDict()
                req_headers['Host'] = self.url_info[0]
                if self.url_info[1] != 443:
                    req_headers['Host'] += ':%d' % self.url_info[1]
                req_headers['Accept-Encoding'] = self.supported_encodings()
                req_headers['Connection'] = 'Keep-Alive'
                user_agent = self.settings.get('user_agent')
                if user_agent:
                    req_headers["User-Agent"] = user_agent
                req_headers = self.add_conditional_headers(url, req_headers)

                request = 'GET '
                url_info = urlparse(url)
                if self.using_proxy:
                    request += url + ' HTTP/1.1'
                else:
                    path = '/' if not url_info.path else url_info.path
                    if url_info.query:
                        path += '?' + url_info.query
                    request += path + ' HTTP/1.1'
                self.write_request(request, req_headers)

                response = self.read_headers()
                if not response:
                    self.close()
                    self.ensure_connected()
                    if reused:
                        tries += 1
                    reused = False
                    continue
                version, code, message, resp_headers = response

                # Read the body to get any remaining data off the socket
                data = self.read_body(code, resp_headers, timeout)

                # Handle cached responses
                if code == 304:
                    return self.cache_result('get', url, code, resp_headers, b'')

                if code == 301:
                    location = resp_headers.get('location')
                    if not isinstance(location, str_cls):
                        raise OscryptoDownloaderException('Missing or duplicate Location HTTP header')
                    if not re.match(r'https?://', location):
                        if not location.startswith('/'):
                            location = os.path.dirname(url_info.path) + location
                        location = url_info.scheme + '://' + url_info.netloc + location
                    return self.download(location, error_message, timeout, tried, prefer_cached)

                # Make sure we obey Github's rate limiting headers
                self.handle_rate_limit(resp_headers, url)

                # Bitbucket and Github return 503 a decent amount
                if code == 503 and tries != 0:
                    if tries and debug:
                        console_write(
                            '''
                            Downloading %s was rate limited, trying again
                            ''',
                            url
                        )
                    continue

                if code != 200:
                    error_string = text.format(
                        '''
                        %s HTTP error %s downloading %s.
                        ''',
                        (error_message, code, url)
                    )

                else:
                    return self.cache_result('get', url, code, resp_headers, data)

            except (oscrypto_errors.TLSVerificationError) as e:
                self.close()
                if debug:
                    self.dump_certificate(e.certificate)
                error_string = text.format(
                    '''
                    %s TLS verification error %s downloading %s.
                    ''',
                    (error_message, str_cls(e), url)
                )

            except (oscrypto_errors.TLSDisconnectError) as e:
                error_string = text.format(
                    '''
                    %s TLS was gracefully closed while downloading %s, trying again.
                    ''',
                    (error_message, url)
                )

                self.close()

                continue

            except (oscrypto_errors.TLSError) as e:
                self.close()
                error_string = text.format(
                    '''
                    %s TLS error %s downloading %s.
                    ''',
                    (error_message, str_cls(e), url)
                )

            except (socket.error):
                # Handle broken pipes/reset connections by creating a new opener, and
                # thus getting new handlers and a new connection
                if debug:
                    console_write(
                        '''
                        Connection went away while trying to download %s, trying again
                        ''',
                        url
                    )

                self.close()

                continue

            except (OSError) as e:
                self.close()
                error_string = text.format(
                    '''
                    %s OS error %s downloading %s.
                    ''',
                    (error_message, unicode_from_os(e), url)
                )
                raise

            break

        if error_string is None:
            plural = 's' if tried > 1 else ''
            error_string = 'Unable to download %s after %d attempt%s' % (url, tried, plural)

        raise DownloaderException(error_string)

    def setup_connection(self, url, timeout):
        """
        :param url:
            The URL to download

        :param timeout:
            The int number of seconds to set the timeout to
        """

        proxy_username = self.settings.get('proxy_username')
        proxy_password = self.settings.get('proxy_password')

        http_proxy = self.settings.get('http_proxy')
        https_proxy = self.settings.get('https_proxy')

        proxy_info = None
        if https_proxy:
            proxy_info = (https_proxy, proxy_username, proxy_password)

        url_info = urlparse(url)
        if url_info.scheme == 'http':
            raise OscryptoDownloaderException('Can not connect to a non-TLS server')
        hostname = url_info.hostname
        port = url_info.port
        if not port:
            port = 443

        reconnect = False
        if self.socket:
            if self.url_info != (hostname, port):
                reconnect = True
            elif self.proxy_info != proxy_info:
                reconnect = True

        if reconnect:
            self.close()

        if self.socket is None and self.debug:
            console_write(
                '''
                Oscrypto Debug Proxy
                  http_proxy: %s
                  https_proxy: %s
                  proxy_username: %s
                  proxy_password: %s
                ''',
                (http_proxy, https_proxy, proxy_username, proxy_password)
            )

        self.timeout = timeout
        self.debug = self.settings.get('debug')
        self.user_agent = self.settings.get('user_agent')
        self.url_info = (hostname, port)
        self.proxy_info = proxy_info

        return self.ensure_connected()

    def ensure_connected(self):
        """
        Make sure a valid tls.TLSSocket() is open to the server
        """

        reused = self.setup_socket()
        if not reused and self.using_proxy:
            self.do_proxy_connect()
        return reused

    def setup_socket(self):
        """
        Create the oscrypto.tls.TLSSocket() object
        """

        if self.socket:
            return True

        extra_trust_roots = []
        user_ca_bundle_path = get_user_ca_bundle_path(self.settings)
        if os.path.exists(user_ca_bundle_path):
            try:
                with open_compat(user_ca_bundle_path, 'rb') as f:
                    file_data = read_compat(f)
                if len(file_data) > 0:
                    for type_name, headers, der_bytes in pem.unarmor(file_data, multiple=True):
                        extra_trust_roots.append(x509.Certificate.load(der_bytes))
            except (ValueError) as e:
                console_write(
                    '''
                    Oscrypto Debug General
                      Error parsing certs file %s: %s
                    ''',
                    (user_ca_bundle_path, str_cls(e))
                )
        session = tls.TLSSession(extra_trust_roots=extra_trust_roots)

        if self.proxy_info and self.proxy_info[0]:
            proxy_url_info = urlparse(self.proxy_info[0])
            proxy_hostname = proxy_url_info.hostname
            proxy_port = proxy_url_info.port
            if not proxy_port:
                if proxy_url_info.scheme == 'http':
                    raise OscryptoDownloaderException('Can not connect to a non-TLS proxy')
                else:
                    proxy_port = 443
            host = proxy_hostname
            port = proxy_port
            self.using_proxy = True
        else:
            host = self.url_info[0]
            port = self.url_info[1]
            self.using_proxy = False
        if self.debug:
            proxy_details = '' if not self.using_proxy else ' (proxying)'
            console_write(
                '''
                Oscrypto Debug General
                  Connecting to %s on port %s%s
                  Using system CA certs plus additional in file at %s
                  Using hostname "%s" for TLS SNI extension
                ''',
                (host, port, proxy_details, user_ca_bundle_path, self.url_info[0])
            )
        self.socket = tls.TLSSocket(host, port, timeout=self.timeout, session=session)
        if self.debug:
            console_write(
                '  Successfully negotiated %s with cipher suite %s',
                (self.socket.protocol, self.socket.cipher_suite),
                prefix=False
            )
            console_write(
                '  Certificate validated for %s',
                host,
                prefix=False
            )
            self.dump_certificate(self.socket.certificate)
        return False

    def write_request(self, request, headers):
        """
        :param request:
            A unicode string of the first line of the HTTP request

        :param headers:
            An OrderedDict of the request headers
        """

        lines = [request]
        for header, value in headers.items():
            lines.append('%s: %s' % (header, value))

        if self.debug:
            console_write(
                '''
                Oscrypto Debug Write
                  %s
                ''',
                '\n  '.join(lines)
            )

        lines.extend(['', ''])

        request = '\r\n'.join(lines).encode('iso-8859-1')
        self.socket.write(request)

    def read_headers(self):
        """
        Reads the HTTP response headers from the socket

        :return:
            On error, None, otherwise a 4-element tuple:
              0: A 2-element tuple of integers representing the HTTP version
              1: An integer representing the HTTP response code
              2: A unicode string of the HTTP response code name
              3: An OrderedDict of HTTP headers with lowercase unicode key and unicode values
        """

        version = None
        code = None
        text = None
        headers = OrderedDict()

        data = self.socket.read_until(b'\r\n\r\n')
        string = data.decode('iso-8859-1')
        if self.debug:
            lines = []
        first = True
        for line in string.split('\r\n'):
            line = line.strip()
            if len(line) == 0:
                continue
            if self.debug:
                lines.append(line)
            if first:
                match = re.match(r'^HTTP/(1\.[01]) +(\d+) +(.*)$', line)
                if not match:
                    if self.debug:
                        console_write(
                            '''
                            Oscrypto Debug Read
                              %s
                            ''',
                            '\n  '.join(lines)
                        )
                    return None
                version = tuple(map(int, match.group(1).split('.')))
                code = int(match.group(2))
                text = match.group(3)
                first = False
            else:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    name = parts[0].strip().lower()
                    value = parts[1].strip()
                    if name in headers:
                        headers[name] += ', %s' % value
                    else:
                        headers[name] = value

        if self.debug:
            console_write(
                '''
                Oscrypto Debug Read
                  %s
                ''',
                '\n  '.join(lines)
            )

        return (version, code, text, headers)

    def parse_content_length(self, headers):
        """
        Returns the content-length from a dict of headers

        :return:
            An integer of the content length
        """

        content_length = headers.get('content-length')
        if isinstance(content_length, str_cls) and len(content_length) > 0:
            content_length = int(content_length)
        return content_length

    def read_body(self, code, resp_headers, timeout):
        """
        Reads the plaintext body of the request

        :param code:
            The integer HTTP response code

        :param resp_headers:
            A dict of the response headers

        :param timeout:
            An integer number of seconds to timeout a read

        :return:
            A byte string of the decompressed plain text body
        """

        # Should adhere to https://tools.ietf.org/html/rfc7230#section-3.3.3

        data = b''
        transfer_encoding = resp_headers.get('transfer-encoding')
        if transfer_encoding and transfer_encoding.lower() == 'chunked':
            while True:
                line = self.socket.read_until(b'\r\n').decode('iso-8859-1').rstrip()
                if re.match(r'^[a-fA-F0-9]+$', line):
                    chunk_length = int(line, 16)
                    if chunk_length == 0:
                        break
                    data += self.socket.read_exactly(chunk_length)
                    if self.socket.read_exactly(2) != b'\r\n':
                        raise OscryptoDownloaderException('Unable to parse chunk newline')
                else:
                    self.close()
                    raise OscryptoDownloaderException('Unable to parse chunk length')
        else:
            content_length = self.parse_content_length(resp_headers)
            if content_length is not None:
                if content_length > 0:
                    data = self.socket.read_exactly(content_length)
            elif code == 204 or code == 304 or (code >= 100 and code < 200):
                # These HTTP codes are defined to not have a body
                pass
            elif resp_headers.get('connection', '').lower() == 'keep-alive':
                # If the connection is kept-alive, and there is no content-length,
                # and not chunked, than the response has an empty body.
                pass
            else:
                # This should only happen if the server is going to close the connection
                while self.socket.select_read(timeout=timeout):
                    data += self.socket.read(8192)
                self.close()

        if resp_headers.get('connection', '').lower() == 'close':
            self.close()

        encoding = resp_headers.get('content-encoding')
        return self.decode_response(encoding, data)

    def dump_certificate(self, cert):
        """
        If debugging is enabled, dumps info about the certificate
        the server returned
        """

        if self.debug:
            sig_algo_names = {
                'rsassa_pkcs1v15': 'RSA PKCS #1 v1.5',
                'dsa': 'DSA',
                'ecdsa': 'ECDSA',
                'rsassa_pss': 'RSA PSS',
            }
            signature_algo = sig_algo_names[cert.signature_algo]
            public_key_algo = cert.public_key.algorithm.upper()
            if public_key_algo == 'EC':
                curve_info = cert.public_key.curve
                if curve_info[0] == 'named':
                    public_key_algo += ' ' + curve_info[1]
            else:
                public_key_algo += ' ' + str_cls(cert.public_key.bit_size)
            console_write(
                '''
                Oscrypto Server TLS Certificate
                  subject: %s
                  serial: %s
                  issuer: %s
                  expires: %s
                  valid domains: %s
                  public key algo: %s
                  signature algo: %s
                  sha256 fingerprint: %s
                ''',
                (
                    cert.subject.human_friendly,
                    cert.serial_number,
                    cert.issuer.human_friendly,
                    cert['tbs_certificate']['validity']['not_after'].chosen.native.strftime('%Y-%m-%d %H:%M:%S %z').strip(),
                    ', '.join(cert.valid_domains),
                    public_key_algo,
                    signature_algo,
                    cert.sha256_fingerprint,
                )
            )

    def do_proxy_connect(self, headers=None):
        """
        Send the CONNECT request to the proxy server
        """

        req_headers = OrderedDict()
        req_headers['Host'] = '%s:%s' % self.url_info
        req_headers['User-Agent'] = self.user_agent
        req_headers['Accept-Encoding'] = self.supported_encodings()
        req_headers['Proxy-Connection'] = 'Keep-Alive'

        self.write_request('CONNECT %s:%d HTTP/1.1' % self.url_info, req_headers)
        response = self.read_headers()
        if not response:
            raise OscryptoDownloaderException('Unable to parse response headers')
        version, code, message, resp_headers = response

        content_length = self.parse_content_length(resp_headers)

        close = False
        for header in ('connection', 'proxy-connection'):
            value = resp_headers.get(header)
            if isinstance(value, str_cls) and value.lower() == 'close':
                close = True

        if close:
            self.socket.close()
            self.socket = None
            self.setup_socket()

        # According to RFC 7230, there must be no content in the
        # response to a CONNECT request, so we don't read anymore

        # Handle proxy auth for SSL connections since regular urllib punts on this
        if code == 407 and self.proxy_info[1] and headers is None:
            supported_auth_methods = {}
            values = resp_headers.get('proxy-authenticate', tuple())
            for value in values:
                details = value.split(' ', 1)
                supported_auth_methods[details[0].lower()] = details[1] if len(details) > 1 else ''

            req_headers = OrderedDict()

            username = self.proxy_info[1]
            password = self.proxy_info[2]
            if 'digest' in supported_auth_methods:
                response_value = self.build_digest_response(
                    supported_auth_methods['digest'], username, password)
                if response_value:
                    req_headers['Proxy-Authorization'] = 'Digest %s' % response_value

            elif 'basic' in supported_auth_methods:
                response_value = '%s:%s' % (username, password)
                response_value = base64.b64encode(response_value.encode('utf-8')).decode('utf-8')
                req_headers['Proxy-Authorization'] = 'Basic %s' % response_value.strip()

            return self.do_proxy_connect(req_headers)

        if code != 200:
            self.close()
            raise OscryptoDownloaderException("Tunnel connection failed: %d %s" % (code, message))

    def build_digest_response(self, fields, username, password):
        """
        Takes a Proxy-Authenticate: Digest header and creates a response
        header

        :param fields:
            The string portion of the Proxy-Authenticate header after
            "Digest "

        :param username:
            The username to use for the response

        :param password:
            The password to use for the response

        :return:
            None if invalid Proxy-Authenticate header, otherwise the
            string of fields for the Proxy-Authorization: Digest header
        """

        fields = parse_keqv_list(parse_http_list(fields))

        realm = fields.get('realm')
        nonce = fields.get('nonce')
        qop = fields.get('qop')
        algorithm = fields.get('algorithm')
        if algorithm:
            algorithm = algorithm.lower()
        opaque = fields.get('opaque')

        if algorithm in ('md5', None):
            def md5hash(string):
                return hashlib.md5(string).hexdigest()
            _hash = md5hash

        elif algorithm == 'sha':
            def sha1hash(string):
                return hashlib.sha1(string).hexdigest()
            _hash = sha1hash

        else:
            return None

        host_port = '%s:%s' % self.url_info

        a1 = '%s:%s:%s' % (username, realm, password)
        a2 = 'CONNECT:%s' % host_port
        ha1 = _hash(a1)
        ha2 = _hash(a2)

        if qop is None:
            response = _hash('%s:%s:%s' % (ha1, nonce, ha2))
        elif qop == 'auth':
            nc = '00000001'
            cnonce = _hash(os.urandom(8))[:8]
            response = _hash('%s:%s:%s:%s:%s:%s' % (ha1, nonce, nc, cnonce, qop, ha2))
        else:
            return None

        resp_fields = OrderedDict()
        resp_fields['username'] = username
        resp_fields['realm'] = realm
        resp_fields['nonce'] = nonce
        resp_fields['response'] = response
        resp_fields['uri'] = host_port
        if algorithm:
            resp_fields['algorithm'] = algorithm
        if qop == 'auth':
            resp_fields['nc'] = nc
            resp_fields['cnonce'] = cnonce
            resp_fields['qop'] = qop
        if opaque:
            resp_fields['opaque'] = opaque

        return ', '.join(['%s="%s"' % (field, resp_fields[field]) for field in resp_fields])

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """
        return True

    def supports_plaintext(self):
        """
        Indicates if the object can handle non-secure HTTP requests

        :return:
            If the object supports non-secure HTTP requests
        """

        return False
