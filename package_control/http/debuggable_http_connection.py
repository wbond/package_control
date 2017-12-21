import socket

from http.client import HTTPConnection

from ..console_write import console_write
from .debuggable_http_response import DebuggableHTTPResponse


class DebuggableHTTPConnection(HTTPConnection):

    """
    A custom HTTPConnection that formats debugging info for Sublime Text
    """

    response_class = DebuggableHTTPResponse
    _debug_protocol = 'HTTP'

    def __init__(self, host, port=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, **kwargs):
        self.passwd = kwargs.get('passwd')
        if kwargs.get('debug'):
            self.debuglevel = 5
        elif 'debuglevel' in kwargs:
            self.debuglevel = kwargs['debuglevel']

        HTTPConnection.__init__(self, host, port=port, timeout=timeout)

    def connect(self):
        if self.debuglevel == -1:
            console_write(
                '''
                Urllib %s Debug General
                  Connecting to %s on port %s
                ''',
                (self._debug_protocol, self.host, self.port)
            )
        HTTPConnection.connect(self)

    def send(self, data):
        # We have to use a positive debuglevel to get it passed to the
        # HTTPResponse object, however we don't want to use it because by
        # default debugging prints to the stdout and we can't capture it, so
        # we temporarily set it to -1 for the standard httplib code
        reset_debug = False
        if self.debuglevel == 5:
            reset_debug = 5
            self.debuglevel = -1
        HTTPConnection.send(self, data)
        if reset_debug or self.debuglevel == -1:
            data = data.strip()
            if data:
                string = data.decode('iso-8859-1')
                indented_headers = '\n  '.join(string.splitlines())
                console_write(
                    '''
                    Urllib %s Debug Write
                      %s
                    ''',
                    (self._debug_protocol, indented_headers)
                )
            if reset_debug:
                self.debuglevel = reset_debug

    def request(self, method, url, body=None, headers={}):
        original_headers = headers.copy()

        # By default urllib2 and urllib.request override the Connection header,
        # however, it is preferred to be able to re-use it
        original_headers['Connection'] = 'Keep-Alive'

        HTTPConnection.request(self, method, url, body, original_headers)
