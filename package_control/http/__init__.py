import sys

try:
    # Python 2
    import urllib2

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

    # Money patch urllib2.Request for Python 2.6.1-2
    if sys.version_info < (2, 6, 3):

        urllib2.Request._tunnel_host = None

        def py268_set_proxy(self, host, type):
            if self.type == 'https' and not self._tunnel_host:
                self._tunnel_host = self.host
            else:
                self.type = type
                self.__r_host = self.__original
            self.host = host
        urllib2.Request.set_proxy = py268_set_proxy

except (ImportError):
    # Python 3 does not need to be patched
    pass
