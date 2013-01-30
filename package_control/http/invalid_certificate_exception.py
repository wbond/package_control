import httplib
import urllib2


class InvalidCertificateException(httplib.HTTPException, urllib2.URLError):
    """
    An exception for when an SSL certification is not valid for the URL
    it was presented for.
    """

    def __init__(self, host, cert, reason):
        httplib.HTTPException.__init__(self)
        self.host = host
        self.cert = cert
        self.reason = reason

    def __str__(self):
        return ('Host %s returned an invalid certificate (%s) %s\n' %
            (self.host, self.reason, self.cert))
