import sys

try:
    # Python 2
    import urllib2
    import httplib

    # Monkey patch AbstractBasicAuthHandler to prevent infinite recursion
    def non_recursive_http_error_auth_reqed(self, authreq, host, req, headers):
        authreq = headers.get(authreq, None)

        if not hasattr(self, 'retried'):
            self.retried = 0

        if self.retried > 5:
            raise urllib2.HTTPError(req.get_full_url(), 401, "basic auth failed",
                headers, None)
        else:
            self.retried += 1

        if authreq:
            mo = urllib2.AbstractBasicAuthHandler.rx.search(authreq)
            if mo:
                scheme, quote, realm = mo.groups()
                if scheme.lower() == 'basic':
                    return self.retry_http_basic_auth(host, req, realm)

    urllib2.AbstractBasicAuthHandler.http_error_auth_reqed = non_recursive_http_error_auth_reqed

    # Money patch urllib2.Request and httplib.HTTPConnection so that
    # HTTPS proxies work in Python 2.6.1-2
    if sys.version_info < (2, 6, 3):

        urllib2.Request._tunnel_host = None

        def py268_set_proxy(self, host, type):
            if self.type == 'https' and not self._tunnel_host:
                self._tunnel_host = self.host
            else:
                self.type = type
                # The _Request prefix is to handle python private name mangling
                self._Request__r_host = self._Request__original
            self.host = host
        urllib2.Request.set_proxy = py268_set_proxy

    if sys.version_info < (2, 6, 5):

        def py268_set_tunnel(self, host, port=None, headers=None):
            """ Sets up the host and the port for the HTTP CONNECT Tunnelling.

            The headers argument should be a mapping of extra HTTP headers
            to send with the CONNECT request.
            """
            self._tunnel_host = host
            self._tunnel_port = port
            if headers:
                self._tunnel_headers = headers
            else:
                self._tunnel_headers.clear()
        httplib.HTTPConnection._set_tunnel = py268_set_tunnel


except (ImportError):
    # Python 3 does not need to be patched
    pass
