import re
import socket
import base64
import hashlib
import os
import sys

try:
    # Python 3
    from http.client import HTTPS_PORT
    from urllib.request import parse_keqv_list, parse_http_list
    x509 = None
except (ImportError):
    # Python 2
    from httplib import HTTPS_PORT
    from urllib2 import parse_keqv_list, parse_http_list
    from . import x509

from ..console_write import console_write
from .debuggable_https_response import DebuggableHTTPSResponse
from .debuggable_http_connection import DebuggableHTTPConnection
from .invalid_certificate_exception import InvalidCertificateException


# The following code is wrapped in a try because the Linux versions of Sublime
# Text do not include the ssl module due to the fact that different distros
# have different versions
try:
    import ssl

    class ValidatingHTTPSConnection(DebuggableHTTPConnection):
        """
        A custom HTTPConnection class that validates SSL certificates, and
        allows proxy authentication for HTTPS connections.
        """

        default_port = HTTPS_PORT

        response_class = DebuggableHTTPSResponse
        _debug_protocol = 'HTTPS'

        def __init__(self, host, port=None, key_file=None, cert_file=None,
                ca_certs=None, **kwargs):
            passed_args = {}
            if 'timeout' in kwargs:
                passed_args['timeout'] = kwargs['timeout']
            if 'debug' in kwargs:
                passed_args['debug'] = kwargs['debug']
            DebuggableHTTPConnection.__init__(self, host, port, **passed_args)

            self.passwd = kwargs.get('passwd')
            self.key_file = key_file
            self.cert_file = cert_file
            self.ca_certs = ca_certs
            if 'user_agent' in kwargs:
                self.user_agent = kwargs['user_agent']
            if self.ca_certs:
                self.cert_reqs = ssl.CERT_REQUIRED
            else:
                self.cert_reqs = ssl.CERT_NONE

        def get_valid_hosts_for_cert(self, cert):
            """
            Returns a list of valid hostnames for an SSL certificate

            :param cert: A dict from SSLSocket.getpeercert()

            :return: An array of hostnames
            """

            if 'subjectAltName' in cert:
                return [x[1] for x in cert['subjectAltName']
                             if x[0].lower() == 'dns']
            else:
                return [x[0][1] for x in cert['subject']
                                if x[0][0].lower() == 'commonname']

        def validate_cert_host(self, cert, hostname):
            """
            Checks if the cert is valid for the hostname

            :param cert: A dict from SSLSocket.getpeercert()

            :param hostname: A string hostname to check

            :return: A boolean if the cert is valid for the hostname
            """

            hosts = self.get_valid_hosts_for_cert(cert)
            for host in hosts:
                host_re = host.replace('.', '\.').replace('*', '[^.]*')
                if re.search('^%s$' % (host_re,), hostname, re.I):
                    return True
            return False

        def _tunnel(self):
            """
            This custom _tunnel method allows us to read and print the debug
            log for the whole response before throwing an error, and adds
            support for proxy authentication
            """

            self._proxy_host = self.host
            self._proxy_port = self.port
            self._set_hostport(self._tunnel_host, self._tunnel_port)

            self._tunnel_headers['Host'] = u"%s:%s" % (self.host, self.port)
            self._tunnel_headers['User-Agent'] = self.user_agent
            self._tunnel_headers['Proxy-Connection'] = 'Keep-Alive'

            request = "CONNECT %s:%d HTTP/1.1\r\n" % (self.host, self.port)
            for header, value in self._tunnel_headers.items():
                request += "%s: %s\r\n" % (header, value)
            request += "\r\n"

            if sys.version_info >= (3,):
                request = bytes(request, 'iso-8859-1')

            self.send(request)

            response = self.response_class(self.sock, method=self._method)
            (version, code, message) = response._read_status()

            status_line = u"%s %s %s" % (version, code, message.rstrip())
            headers = [status_line]

            if self.debuglevel in [-1, 5]:
                console_write(u'Urllib %s Debug Read' % self._debug_protocol, True)
                console_write(u"  %s" % status_line)

            content_length = 0
            close_connection = False
            while True:
                line = response.fp.readline()

                if sys.version_info >= (3,):
                    line = str(line, encoding='iso-8859-1')

                if line == '\r\n':
                    break

                headers.append(line.rstrip())

                parts = line.rstrip().split(': ', 1)
                name = parts[0].lower()
                value = parts[1].lower().strip()
                if name == 'content-length':
                    content_length = int(value)

                if name in ['connection', 'proxy-connection'] and value == 'close':
                    close_connection = True

                if self.debuglevel in [-1, 5]:
                    console_write(u"  %s" % line.rstrip())

            # Handle proxy auth for SSL connections since regular urllib punts on this
            if code == 407 and self.passwd and 'Proxy-Authorization' not in self._tunnel_headers:
                if content_length:
                    response._safe_read(content_length)

                supported_auth_methods = {}
                for line in headers:
                    parts = line.split(': ', 1)
                    if parts[0].lower() != 'proxy-authenticate':
                        continue
                    details = parts[1].split(' ', 1)
                    supported_auth_methods[details[0].lower()] = details[1] if len(details) > 1 else ''

                username, password = self.passwd.find_user_password(None, "%s:%s" % (
                    self._proxy_host, self._proxy_port))

                if 'digest' in supported_auth_methods:
                    response_value = self.build_digest_response(
                        supported_auth_methods['digest'], username, password)
                    if response_value:
                        self._tunnel_headers['Proxy-Authorization'] = u"Digest %s" % response_value

                elif 'basic' in supported_auth_methods:
                    response_value = u"%s:%s" % (username, password)
                    response_value = base64.b64encode(response_value.encode('utf-8')).decode('utf-8')
                    self._tunnel_headers['Proxy-Authorization'] = u"Basic %s" % response_value.strip()

                if 'Proxy-Authorization' in self._tunnel_headers:
                    self.host = self._proxy_host
                    self.port = self._proxy_port

                    # If the proxy wanted the connection closed, we need to make a new connection
                    if close_connection:
                        self.sock.close()
                        self.sock = socket.create_connection((self.host, self.port), self.timeout)

                    return self._tunnel()

            if code != 200:
                self.close()
                raise socket.error("Tunnel connection failed: %d %s" % (code,
                    message.strip()))

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

            if algorithm in ['md5', None]:
                def md5hash(string):
                    return hashlib.md5(string).hexdigest()
                hash = md5hash

            elif algorithm == 'sha':
                def sha1hash(string):
                    return hashlib.sha1(string).hexdigest()
                hash = sha1hash

            else:
                return None

            host_port = u"%s:%s" % (self.host, self.port)

            a1 = "%s:%s:%s" % (username, realm, password)
            a2 = "CONNECT:%s" % host_port
            ha1 = hash(a1)
            ha2 = hash(a2)

            if qop == None:
                response = hash(u"%s:%s:%s" % (ha1, nonce, ha2))
            elif qop == 'auth':
                nc = '00000001'
                cnonce = hash(os.urandom(8))[:8]
                response = hash(u"%s:%s:%s:%s:%s:%s" % (ha1, nonce, nc, cnonce, qop, ha2))
            else:
                return None

            response_fields = {
                'username': username,
                'realm': realm,
                'nonce': nonce,
                'response': response,
                'uri': host_port
            }
            if algorithm:
                response_fields['algorithm'] = algorithm
            if qop == 'auth':
                response_fields['nc'] = nc
                response_fields['cnonce'] = cnonce
                response_fields['qop'] = qop
            if opaque:
                response_fields['opaque'] = opaque

            return ', '.join([u"%s=\"%s\"" % (field, response_fields[field]) for field in response_fields])

        def connect(self):
            """
            Adds debugging and SSL certification validation
            """

            if self.debuglevel == -1:
                console_write(u"Urllib HTTPS Debug General", True)
                console_write(u"  Connecting to %s on port %s" % (self.host, self.port))

            self.sock = socket.create_connection((self.host, self.port), self.timeout)
            if self._tunnel_host:
                self._tunnel()

            if self.debuglevel == -1:
                console_write(u"Urllib HTTPS Debug General", True)
                console_write(u"  Connecting to %s on port %s" % (self.host, self.port))
                console_write(u"  CA certs file at %s" % (self.ca_certs.decode(sys.getfilesystemencoding())))

            self.sock = ssl.wrap_socket(self.sock, keyfile=self.key_file,
                certfile=self.cert_file, cert_reqs=self.cert_reqs,
                ca_certs=self.ca_certs, ssl_version=ssl.PROTOCOL_TLSv1)

            if self.debuglevel == -1:
                cipher_info = self.sock.cipher()
                console_write(u"  Successfully upgraded connection to %s:%s with SSL" % (
                    self.host, self.port))
                console_write(u"  Using %s with cipher %s" % (
                    cipher_info[1], cipher_info[0]))

            # This debugs and validates the SSL certificate
            if self.cert_reqs & ssl.CERT_REQUIRED:
                cert = self.sock.getpeercert()
                # Python 2.6 doesn't seem to parse the subject alt name, so
                # we parse the raw DER certificate and grab the info ourself
                if x509:
                    der_cert = self.sock.getpeercert(True)
                    parsed_cert = x509.parse(der_cert)
                    if 'subjectAltName' in parsed_cert:
                        cert['subjectAltName'] = parsed_cert['subjectAltName']

                if self.debuglevel == -1:
                    subjectMap = {
                        'organizationName': 'O',
                        'commonName': 'CN',
                        'organizationalUnitName': 'OU',
                        'countryName': 'C',
                        'serialNumber': 'serialNumber',
                        'commonName': 'CN',
                        'localityName': 'L',
                        'stateOrProvinceName': 'S',
                        '1.3.6.1.4.1.311.60.2.1.2': 'incorporationState',
                        '1.3.6.1.4.1.311.60.2.1.3': 'incorporationCountry'
                    }
                    subject_list = list(cert['subject'])
                    subject_list.reverse()
                    subject_parts = []
                    for pair in subject_list:
                        if pair[0][0] in subjectMap:
                            field_name = subjectMap[pair[0][0]]
                        else:
                            field_name = pair[0][0]
                        subject_parts.append(field_name + '=' + pair[0][1])

                    console_write(u"  Server SSL certificate:")
                    console_write(u"    subject: " + ','.join(subject_parts))
                    if 'subjectAltName' in cert:
                        alt_names = [c[1] for c in cert['subjectAltName']]
                        alt_names = ', '.join(alt_names)
                        console_write(u"    subject alt name: %s" % alt_names)
                    if 'notAfter' in cert:
                        console_write(u"    expire date: " + cert['notAfter'])

                hostname = self.host.split(':', 0)[0]

                if not self.validate_cert_host(cert, hostname):
                    if self.debuglevel == -1:
                        console_write(u"  Certificate INVALID")

                    raise InvalidCertificateException(hostname, cert,
                        'hostname mismatch')

                if self.debuglevel == -1:
                    console_write(u"  Certificate validated for %s" % hostname)

except (ImportError):
    pass
