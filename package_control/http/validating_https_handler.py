import ssl
from urllib.error import URLError
import urllib.request as urllib_compat

from .validating_https_connection import ValidatingHTTPSConnection
from .invalid_certificate_exception import InvalidCertificateException
from .persistent_handler import PersistentHandler


class ValidatingHTTPSHandler(PersistentHandler, urllib_compat.HTTPSHandler):

    """
    A urllib handler that validates SSL certificates for HTTPS requests
    """

    def __init__(self, **kwargs):
        # This is a special value that will not trigger the standard debug
        # functionality, but custom code where we can format the output
        self._debuglevel = 0
        if 'debug' in kwargs and kwargs['debug']:
            self._debuglevel = 5
        elif 'debuglevel' in kwargs:
            self._debuglevel = kwargs['debuglevel']
        self._connection_args = kwargs

    def https_open(self, req):
        def http_class_wrapper(host, **kwargs):
            full_kwargs = dict(self._connection_args)
            full_kwargs.update(kwargs)
            return ValidatingHTTPSConnection(host, **full_kwargs)

        try:
            return self.do_open(http_class_wrapper, req)
        except URLError as e:
            if type(e.reason) == ssl.SSLError and e.reason.args[0] == 1:
                raise InvalidCertificateException(req.host, '',
                                                  e.reason.args[1])
            raise

    https_request = urllib_compat.AbstractHTTPHandler.do_request_
