try:
    # Python 3
    from urllib.request import BaseHandler, HTTPPasswordMgr
except (ImportError):
    # Python 2
    from urllib2 import BaseHandler, HTTPPasswordMgr

import os

if os.name == 'nt':
    try:
        # Python 3
        from ...lib.windows.ntlm import ntlm
    except (ValueError):
        # Python 2
        from ntlm import ntlm
        

if os.name == 'nt':
    class ProxyNtlmAuthHandler(BaseHandler):
        """
        Provides NTLM authentication for proxy servers.
        """

        handler_order = 300
        auth_header = 'Proxy-Authorization'

        def __init__(self, password_manager=None):
            if password_manager is None:
                password_manager = HTTPPasswordMgr()
            self.passwd = password_manager
            self.retried = 0

        def http_error_407(self, req, fp, code, msg, headers):
            proxy_authenticate = headers.get('proxy-authenticate')
            if os.name != 'nt' or proxy_authenticate[0:4] != 'NTLM':
                return None

            type1_flags = ntlm.NTLM_TYPE1_FLAGS

            if req.host.find(':') != -1:
                host_port = req.host
            else:
                host_port = "%s:%s" % (req.host, req.port)
            username, password = self.passwd.find_user_password(None, host_port)
            if not username:
                return None

            if username.find('\\') == -1:
                type1_flags &= ~ntlm.NTLM_NegotiateOemDomainSupplied

            negotiate_message = ntlm.create_NTLM_NEGOTIATE_MESSAGE(username, type1_flags)
            auth = 'NTLM %s' % negotiate_message
            if req.headers.get(self.auth_header, None) == auth:
                return None
            req.add_unredirected_header(self.auth_header, auth)
            return self.parent.open(req, timeout=req.timeout)

else:

    # Let the user know if this is used on an unsupported platform
    class ProxyNtlmAuthHandler(BaseHandler):
        def __init__(self, password_manager=None):
            raise Exception("ProxyNtlmAuthHandler is only implemented on Windows")
