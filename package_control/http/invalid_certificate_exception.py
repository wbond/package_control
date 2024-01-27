from http.client import HTTPException
from urllib.error import URLError


class InvalidCertificateException(HTTPException, URLError):

    """
    An exception for when an SSL certification is not valid for the URL
    it was presented for.
    """

    def __init__(self, host, cert, reason):
        self.host = host
        self.cert = cert
        self.reason = reason.rstrip()
        message = 'Host %s returned an invalid certificate (%s) %s' % (self.host, self.reason, self.cert)
        HTTPException.__init__(self, message.rstrip())
