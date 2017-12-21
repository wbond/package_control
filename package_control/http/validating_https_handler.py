# The following code is wrapped in a try because the Linux versions of Sublime
# Text do not include the ssl module due to the fact that different distros
# have different versions
try:
    import ssl

    from urllib.error import URLError
    from urllib.request import AbstractHTTPHandler
    from urllib.request import HTTPSHandler

    from .invalid_certificate_exception import InvalidCertificateException
    from .persistent_handler import PersistentHandler
    from .validating_https_connection import ValidatingHTTPSConnection

    class ValidatingHTTPSHandler(PersistentHandler, HTTPSHandler):

        """
        A urllib handler that validates SSL certificates for HTTPS requests
        """

        def __init__(self, **kwargs):
            # This is a special value that will not trigger the standard debug
            # functionality, but custom code where we can format the output
            self._debuglevel = 0
            if kwargs.get('debug'):
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
                if isinstance(e.reason, ssl.SSLError) and e.reason.args[0] == 1:
                    raise InvalidCertificateException(req.host, '', e.reason.args[1])
                raise

        https_request = AbstractHTTPHandler.do_request_

    HAVE_SSL_SUPPORT = True

except (ImportError) as e:

    HAVE_SSL_SUPPORT = False

    import_error = e

    class ValidatingHTTPSHandler():

        def __init__(self, **kwargs):
            raise import_error
