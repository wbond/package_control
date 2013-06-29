import sys
import socket

try:
    # Python 3
    from urllib.error import URLError
except ImportError:
    # Python 2
    from urllib2 import URLError
    from urllib import addinfourl

from ..console_write import console_write


class PersistentHandler:
    connection = None
    use_count = 0

    def close(self):
        if self.connection:
            if self._debuglevel == 5:
                s = '' if self.use_count == 1 else 's'
                console_write(u"Urllib %s Debug General" % self.connection._debug_protocol, True)
                console_write(u"  Closing connection to %s on port %s after %s request%s" % (
                    self.connection.host, self.connection.port, self.use_count, s))
            self.connection.close()
            self.connection = None
            self.use_count = 0

    def do_open(self, http_class, req):
        # Large portions from Python 3.3 Lib/urllib/request.py and
        # Python 2.6 Lib/urllib2.py

        if sys.version_info >= (3,):
            host = req.host
        else:
            host = req.get_host()

        if not host:
            raise URLError('no host given')

        if self.connection and self.connection.host != host:
            self.close()

        # Re-use the connection if possible
        self.use_count += 1
        if not self.connection:
            h = http_class(host, timeout=req.timeout)
        else:
            h = self.connection
            if self._debuglevel == 5:
                console_write(u"Urllib %s Debug General" % h._debug_protocol, True)
                console_write(u"  Re-using connection to %s on port %s for request #%s" % (
                    h.host, h.port, self.use_count))

        if sys.version_info >= (3,):
            headers = dict(req.unredirected_hdrs)
            headers.update(dict((k, v) for k, v in req.headers.items()
                                if k not in headers))
            headers = dict((name.title(), val) for name, val in headers.items())

        else:
            h.set_debuglevel(self._debuglevel)

            headers = dict(req.headers)
            headers.update(req.unredirected_hdrs)
            headers = dict(
                (name.title(), val) for name, val in headers.items())

        if req._tunnel_host and not self.connection:
            tunnel_headers = {}
            proxy_auth_hdr = "Proxy-Authorization"
            if proxy_auth_hdr in headers:
                tunnel_headers[proxy_auth_hdr] = headers[proxy_auth_hdr]
                del headers[proxy_auth_hdr]

            if sys.version_info >= (3,):
                h.set_tunnel(req._tunnel_host, headers=tunnel_headers)
            else:
                h._set_tunnel(req._tunnel_host, headers=tunnel_headers)

        try:
            if sys.version_info >= (3,):
                h.request(req.get_method(), req.selector, req.data, headers)
            else:
                h.request(req.get_method(), req.get_selector(), req.data, headers)
        except socket.error as err: # timeout error
            h.close()
            raise URLError(err)
        else:
            r = h.getresponse()

        # Keep the connection around for re-use
        if r.is_keep_alive():
            self.connection = h
        else:
            if self._debuglevel == 5:
                s = '' if self.use_count == 1 else 's'
                console_write(u"Urllib %s Debug General" % h._debug_protocol, True)
                console_write(u"  Closing connection to %s on port %s after %s request%s" % (
                    h.host, h.port, self.use_count, s))
            self.use_count = 0
            self.connection = None

        if sys.version_info >= (3,):
            r.url = req.get_full_url()
            r.msg = r.reason
            return r

        r.recv = r.read
        fp = socket._fileobject(r, close=True)

        resp = addinfourl(fp, r.msg, req.get_full_url())
        resp.code = r.status
        resp.msg = r.reason
        return resp
