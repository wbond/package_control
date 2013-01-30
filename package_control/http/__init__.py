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

except (ImportError):
    # Python 3 does not need to be patched
    pass