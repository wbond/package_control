try:
    # Python 3
    from urllib.error import URLError
    import urllib.request as urllib_compat
except (ImportError):
    # Python 2
    from urllib2 import URLError
    import urllib2 as urllib_compat


# The following code is wrapped in a try because the Linux versions of Sublime
# Text do not include the ssl module due to the fact that different distros
# have different versions
try:
    import ssl

    from .validating_https_connection import ValidatingHTTPSConnection
    from .invalid_certificate_exception import InvalidCertificateException
    from .persistent_handler import PersistentHandler

    if hasattr(urllib_compat, 'HTTPSHandler'):
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
    else:
        raise ImportError()

except (ImportError) as e:

    class ValidatingHTTPSHandler():
        def __init__(self, **kwargs):
            raise e
