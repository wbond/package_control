try:
    # Python 3
    from io import BytesIO as StringIO
except (ImportError):
    # Python 2
    from StringIO import StringIO

import sublime
import os
import re
import gzip
import zlib

from ..console_write import console_write
from ..open_compat import open_compat

class Downloader():
    """
    A base downloader that actually performs downloading URLs

    The SSL module is not included with the bundled Python for Linux
    users of Sublime Text, so Linux machines will fall back to using curl
    or wget for HTTPS URLs.
    """

    def check_certs(self, domain, timeout):
        """
        Ensures that the SSL CA cert for a domain is present on the machine

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :return:
            The CA cert bundle path on success, or False on error
        """

        cert_match = False

        certs_list = self.settings.get('certs', {})
        certs_dir = os.path.join(sublime.packages_path(), 'Package Control',
            'certs')
        ca_bundle_path = os.path.join(certs_dir, 'ca-bundle.crt')

        cert_info = certs_list.get(domain)
        if cert_info:
            cert_match = self.locate_cert(certs_dir, cert_info[0],
                cert_info[1], domain, timeout)

        wildcard_info = certs_list.get('*')
        if wildcard_info:
            cert_match = self.locate_cert(certs_dir, wildcard_info[0],
                wildcard_info[1], domain, timeout) or cert_match

        if not cert_match:
            console_write(u'No CA certs available for %s.' % domain, True)
            return False

        return ca_bundle_path

    def locate_cert(self, certs_dir, cert_id, location, domain, timeout):
        """
        Makes sure the SSL cert specified has been added to the CA cert
        bundle that is present on the machine

        :param certs_dir:
            The path of the folder that contains the cert files

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param location:
            An http(s) URL, or absolute filesystem path to the CA cert(s)

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :return:
            If the cert specified (by cert_id) is present on the machine and
            part of the ca-bundle.crt file in the certs_dir
        """

        cert_path = os.path.join(certs_dir, cert_id)
        if not os.path.exists(cert_path):
            if str(location) != '':
                if re.match('^https?://', location):
                    contents = self.download_cert(cert_id, location, domain,
                        timeout)
                else:
                    contents = self.load_cert(cert_id, location)
                if contents:
                    self.save_cert(certs_dir, cert_id, contents)
                    return True
            return False
        return True

    def download_cert(self, cert_id, url, domain, timeout):
        """
        Downloads CA cert(s) from a URL

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param url:
            An http(s) URL to the CA cert(s)

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :return:
            The contents of the CA cert(s)
        """

        cert_downloader = self.__class__(self.settings)
        return cert_downloader.download(url,
            'Error downloading CA certs for %s.' % domain, timeout, 1)

    def load_cert(self, cert_id, path):
        """
        Copies CA cert(s) from a file path

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param path:
            The absolute filesystem path to a file containing the CA cert(s)

        :return:
            The contents of the CA cert(s)
        """

        if os.path.exists(path):
            with open_compat(path, 'rb') as f:
                return f.read()

    def save_cert(self, certs_dir, cert_id, contents):
        """
        Saves CA cert(s) to the certs_dir (and ca-bundle.crt file)

        :param certs_dir:
            The path of the folder that contains the cert files

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param contents:
            The contents of the CA cert(s)
        """

        ca_bundle_path = os.path.join(certs_dir, 'ca-bundle.crt')
        cert_path = os.path.join(certs_dir, cert_id)
        with open_compat(cert_path, 'wb') as f:
            f.write(contents)
        with open_compat(ca_bundle_path, 'ab') as f:
            f.write("\n" + contents)

    def decode_response(self, encoding, response):
        if encoding == 'gzip':
            return gzip.GzipFile(fileobj=StringIO(response)).read()
        elif encoding == 'deflate':
            decompresser = zlib.decompressobj(-zlib.MAX_WBITS)
            return decompresser.decompress(response) + decompresser.flush()
        return response
