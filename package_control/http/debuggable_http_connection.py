try:
    # Python 3
    from http.client import HTTPConnection
    from urllib.error import URLError
except (ImportError):
    # Python 2
    from httplib import HTTPConnection
    from urllib2 import URLError

import os
import re
import socket

if os.name == 'nt':
    try:
        # Python 3
        from ...lib.windows.ntlm import ntlm
    except (ValueError):
        # Python 2
        from ntlm import ntlm

from ..console_write import console_write
from .debuggable_http_response import DebuggableHTTPResponse


class DebuggableHTTPConnection(HTTPConnection):
    """
    A custom HTTPConnection that formats debugging info for Sublime Text
    """

    response_class = DebuggableHTTPResponse
    _debug_protocol = 'HTTP'

    def __init__(self, host, port=None, strict=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, **kwargs):
        self.passwd = kwargs.get('passwd')

        # Python 2.6.1 on OS X 10.6 does not include these
        self._tunnel_host = None
        self._tunnel_port = None
        self._tunnel_headers = {}

        HTTPConnection.__init__(self, host, port, strict, timeout)

    def connect(self):
        if self.debuglevel == -1:
            console_write(u'Urllib %s Debug General' % self._debug_protocol, True)
            console_write(u"  Connecting to %s on port %s" % (self.host, self.port))
        HTTPConnection.connect(self)

    def send(self, string):
        # We have to use a positive debuglevel to get it passed to the
        # HTTPResponse object, however we don't want to use it because by
        # default debugging prints to the stdout and we can't capture it, so
        # we temporarily set it to -1 for the standard httplib code
        reset_debug = False
        if self.debuglevel == 5:
            reset_debug = 5
            self.debuglevel = -1
        HTTPConnection.send(self, string)
        if reset_debug or self.debuglevel == -1:
            if len(string.strip()) > 0:
                console_write(u'Urllib %s Debug Write' % self._debug_protocol, True)
                for line in string.strip().splitlines():
                    console_write(u'  ' + line)
            if reset_debug:
                self.debuglevel = reset_debug

    def request(self, method, url, body=None, headers={}):
        original_headers = headers.copy()

        # Handles the challenge request response cycle before the real request
        proxy_auth = headers.get('Proxy-Authorization')
        if os.name == 'nt' and proxy_auth and proxy_auth.lstrip()[0:4] == 'NTLM':
            # The default AbstractHTTPHandler automatically sets the
            # Connection header to close because of urllib.addinfourl(), but in
            # this case we are going to do some back and forth first for the NTLM
            # proxy auth
            headers['Connection'] = 'Keep-Alive'
            self._send_request(method, url, body, headers)

            response = self.getresponse()

            content_length = int(response.getheader('content-length', 0))
            if content_length:
                response._safe_read(content_length)

            proxy_authenticate = response.getheader('proxy-authenticate', None)
            if not proxy_authenticate:
                raise URLError('Invalid NTLM proxy authentication response')
            ntlm_challenge = re.sub('^\s*NTLM\s+', '', proxy_authenticate)

            if self.host.find(':') != -1:
                host_port = self.host
            else:
                host_port = "%s:%s" % (self.host, self.port)
            username, password = self.passwd.find_user_password(None, host_port)
            domain = ''
            user = username
            if username.find('\\') != -1:
                domain, user = username.split('\\', 1)

            challenge, negotiate_flags = ntlm.parse_NTLM_CHALLENGE_MESSAGE(ntlm_challenge)
            new_proxy_authorization = 'NTLM %s' % ntlm.create_NTLM_AUTHENTICATE_MESSAGE(challenge, user,
                domain, password, negotiate_flags)
            original_headers['Proxy-Authorization'] = new_proxy_authorization
            response.close()

        HTTPConnection.request(self, method, url, body, original_headers)
