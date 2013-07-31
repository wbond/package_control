import os
import re
import json

import sublime

from ..console_write import console_write
from ..open_compat import open_compat, read_compat
from ..package_io import read_package_file
from ..cache import get_cache
from ..ca_certs import get_system_ca_bundle_path
from .no_ca_cert_exception import NoCaCertException
from .downloader_exception import DownloaderException


class CertProvider(object):
    """
    A base downloader that provides access to a ca-bundle for validating
    SSL certificates.
    """

    def check_certs(self, domain, timeout):
        """
        Ensures that the SSL CA cert for a domain is present on the machine

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :raises:
            NoCaCertException: when a suitable CA cert could not be found

        :return:
            The CA cert bundle path
        """

        # Try to use the system CA bundle
        ca_bundle_path = get_system_ca_bundle_path(self.settings)
        if ca_bundle_path:
            return ca_bundle_path

        # If the system bundle did not work, fall back to our CA distribution
        # system. Hopefully this will be going away soon.
        if self.settings.get('debug'):
            console_write(u'Unable to find system CA cert bundle, falling back to certs provided by Package Control')

        cert_match = False

        certs_list = get_cache('*.certs', self.settings.get('certs', {}))

        ca_bundle_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-bundle')
        if not os.path.exists(ca_bundle_path) or os.stat(ca_bundle_path).st_size == 0:
            bundle_contents = read_package_file('Package Control', 'Package Control.ca-bundle', True)
            if not bundle_contents:
                raise NoCaCertException(u'Unable to copy distributed Package Control.ca-bundle', domain)
            with open_compat(ca_bundle_path, 'wb') as f:
                f.write(bundle_contents)

        cert_info = certs_list.get(domain)
        if cert_info:
            cert_match = self.locate_cert(cert_info[0],
                cert_info[1], domain, timeout)

        wildcard_info = certs_list.get('*')
        if wildcard_info:
            cert_match = self.locate_cert(wildcard_info[0],
                wildcard_info[1], domain, timeout) or cert_match

        if not cert_match:
            raise NoCaCertException(u'No CA certs available for %s' % domain, domain)

        return ca_bundle_path

    def locate_cert(self, cert_id, location, domain, timeout):
        """
        Makes sure the SSL cert specified has been added to the CA cert
        bundle that is present on the machine

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
            part of the Package Control.ca-bundle file in the User package folder
        """

        ca_list_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-list')
        if not os.path.exists(ca_list_path) or os.stat(ca_list_path).st_size == 0:
            list_contents = read_package_file('Package Control', 'Package Control.ca-list')
            if not list_contents:
                raise NoCaCertException(u'Unable to copy distributed Package Control.ca-list', domain)
            with open_compat(ca_list_path, 'w') as f:
                f.write(list_contents)

        ca_certs = []
        with open_compat(ca_list_path, 'r') as f:
            ca_certs = json.loads(read_compat(f))

        if not cert_id in ca_certs:
            if str(location) != '':
                if re.match('^https?://', location):
                    contents = self.download_cert(cert_id, location, domain,
                        timeout)
                else:
                    contents = self.load_cert(cert_id, location, domain)
                if contents:
                    self.save_cert(cert_id, contents)
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
        if self.settings.get('debug'):
            console_write(u"Downloading CA cert for %s from \"%s\"" % (domain, url), True)
        return cert_downloader.download(url,
            'Error downloading CA certs for %s.' % domain, timeout, 1)

    def load_cert(self, cert_id, path, domain):
        """
        Copies CA cert(s) from a file path

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param path:
            The absolute filesystem path to a file containing the CA cert(s)

        :param domain:
            The domain name the cert is for

        :return:
            The contents of the CA cert(s)
        """

        if os.path.exists(path):
            if self.settings.get('debug'):
                console_write(u"Copying CA cert for %s from \"%s\"" % (domain, path), True)
            with open_compat(path, 'rb') as f:
                return f.read()
        else:
            raise NoCaCertException(u"Unable to find CA cert for %s at \"%s\"" % (domain, path), domain)

    def save_cert(self, cert_id, contents):
        """
        Saves CA cert(s) to the Package Control.ca-bundle

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param contents:
            The contents of the CA cert(s)
        """


        ca_bundle_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-bundle')
        with open_compat(ca_bundle_path, 'ab') as f:
            f.write(b"\n" + contents)

        ca_list_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-list')
        with open_compat(ca_list_path, 'r') as f:
            ca_certs = json.loads(read_compat(f))
        ca_certs.append(cert_id)
        with open_compat(ca_list_path, 'w') as f:
            f.write(json.dumps(ca_certs, indent=4))
