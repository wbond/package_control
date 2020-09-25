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

    def __unicode__(self):
        return self.args[0]

    def __str__(self):
        return self.__unicode__()

    def __bytes__(self):
        return self.__unicode__().encode('utf-8')
