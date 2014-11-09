try:
    # Python 3
    from http.client import HTTPException
    from urllib.error import URLError
except (ImportError):
    # Python 2
    from httplib import HTTPException
    from urllib2 import URLError


class InvalidCertificateException(HTTPException, URLError):
    """
    An exception for when an SSL certification is not valid for the URL
    it was presented for.
    """

    def __init__(self, host, cert, reason):
        self.host = host
        self.cert = cert
        self.reason = reason.rstrip()
        message = ('Host %s returned an invalid certificate (%s) %s' %
            (self.host, self.reason, self.cert)).rstrip()
        HTTPException.__init__(self, message)

    def __str__(self):
        return self.args[0]
