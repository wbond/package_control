import hashlib
import os
import re
import time
import sys

from .cmd import Cli
from .console_write import console_write
from .open_compat import open_compat, read_compat


# Have somewhere to store the CA bundle, even when not running in Sublime Text
try:
    import sublime
    ca_bundle_dir = None
except (ImportError):
    ca_bundle_dir = os.path.join(os.path.expanduser('~'), '.package_control')
    if not os.path.exists(ca_bundle_dir):
        os.mkdir(ca_bundle_dir)


def find_root_ca_cert(settings, domain):
    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))
    binary = runner.retrieve_binary()

    args = [binary, 's_client', '-showcerts', '-connect', domain + ':443']
    result = runner.execute(args, os.path.dirname(binary))

    certs = []
    temp = []

    in_block = False
    for line in result.splitlines():
        if line.find('BEGIN CERTIFICATE') != -1:
            in_block = True
        if in_block:
            temp.append(line)
        if line.find('END CERTIFICATE') != -1:
            in_block = False
            certs.append(u"\n".join(temp))
            temp = []

    # Remove the cert for the domain itself, just leaving the
    # chain cert and the CA cert
    certs.pop(0)

    # Look for the "parent" root CA cert
    subject = openssl_get_cert_subject(settings, certs[-1])
    issuer = openssl_get_cert_issuer(settings, certs[-1])

    cert = get_ca_cert_by_subject(settings, issuer)
    cert_hash = hashlib.md5(cert.encode('utf-8')).hexdigest()

    return [cert, cert_hash]



def get_system_ca_bundle_path(settings):
    """
    Get the filesystem path to the system CA bundle. On Linux it looks in a
    number of predefined places, however on OS X it has to be programatically
    exported from the SystemRootCertificates.keychain. Windows does not ship
    with a CA bundle, but also we use WinINet on Windows, so we don't need to
    worry about CA certs.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :return:
        The full filesystem path to the .ca-bundle file, or False on error
    """

    # If the sublime module is available, we bind this value at run time
    # since the sublime.packages_path() is not available at import time
    global ca_bundle_dir

    platform = sys.platform
    debug = settings.get('debug')

    ca_path = False

    if platform == 'win32':
        console_write(u"Unable to get system CA cert path since Windows does not ship with them", True)
        return False

    # OS X
    if platform == 'darwin':
        if not ca_bundle_dir:
            ca_bundle_dir = os.path.join(sublime.packages_path(), 'User')
        ca_path = os.path.join(ca_bundle_dir, 'Package Control.system-ca-bundle')

        exists = os.path.exists(ca_path)
        # The bundle is old if it is a week or more out of date
        is_old = exists and os.stat(ca_path).st_mtime < time.time() - 604800

        if not exists or is_old:
            if debug:
                console_write(u"Generating new CA bundle from system keychain", True)
            _osx_create_ca_bundle(settings, ca_path)
            if debug:
                console_write(u"Finished generating new CA bundle at %s" % ca_path, True)
        elif debug:
            console_write(u"Found previously exported CA bundle at %s" % ca_path, True)

    # Linux
    else:
        # Common CA cert paths
        paths = [
            '/usr/lib/ssl/certs/ca-certificates.crt',
            '/etc/ssl/certs/ca-certificates.crt',
            '/etc/pki/tls/certs/ca-bundle.crt',
            '/etc/ssl/ca-bundle.pem'
        ]
        for path in paths:
            if os.path.exists(path):
                ca_path = path
                break

        if debug and ca_path:
            console_write(u"Found system CA bundle at %s" % ca_path, True)

    return ca_path


def get_ca_cert_by_subject(settings, subject):
    bundle_path = get_system_ca_bundle_path(settings)

    with open_compat(bundle_path, 'r') as f:
        contents = read_compat(f)

    temp = []

    in_block = False
    for line in contents.splitlines():
        if line.find('BEGIN CERTIFICATE') != -1:
            in_block = True

        if in_block:
            temp.append(line)

        if line.find('END CERTIFICATE') != -1:
            in_block = False
            cert = u"\n".join(temp)
            temp = []

            if openssl_get_cert_subject(settings, cert) == subject:
                return cert

    return False


def openssl_get_cert_issuer(settings, cert):
    """
    Uses the openssl command line client to extract the issuer of an x509
    certificate.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param cert:
        A string containing the PEM-encoded x509 certificate to extract the
        issuer from

    :return:
        The cert issuer
    """

    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))
    binary = runner.retrieve_binary()
    args = [binary, 'x509', '-noout', '-issuer']
    output = runner.execute(args, os.path.dirname(binary), cert)
    return re.sub('^issuer=\s*', '', output)


def openssl_get_cert_name(settings, cert):
    """
    Uses the openssl command line client to extract the name of an x509
    certificate. If the commonName is set, that is used, otherwise the first
    organizationalUnitName is used. This mirrors what OS X uses for storing
    trust preferences.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param cert:
        A string containing the PEM-encoded x509 certificate to extract the
        name from

    :return:
        The cert subject name, which is the commonName (if available), or the
        first organizationalUnitName
    """

    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))

    binary = runner.retrieve_binary()

    args = [binary, 'x509', '-noout', '-subject', '-nameopt',
        'sep_multiline,lname,utf8']
    result = runner.execute(args, os.path.dirname(binary), cert)

    # First look for the common name
    cn = None
    # If there is no common name for the cert, the trust prefs use the first
    # orginizational unit name
    first_ou = None

    for line in result.splitlines():
        match = re.match('^\s+commonName=(.*)$', line)
        if match:
            cn = match.group(1)
            break
        match = re.match('^\s+organizationalUnitName=(.*)$', line)
        if first_ou is None and match:
            first_ou = match.group(1)
            continue

    # This is the name of the cert that would be used in the trust prefs
    return cn or first_ou


def openssl_get_cert_subject(settings, cert):
    """
    Uses the openssl command line client to extract the subject of an x509
    certificate.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param cert:
        A string containing the PEM-encoded x509 certificate to extract the
        subject from

    :return:
        The cert subject
    """

    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))
    binary = runner.retrieve_binary()
    args = [binary, 'x509', '-noout', '-subject']
    output = runner.execute(args, os.path.dirname(binary), cert)
    return re.sub('^subject=\s*', '', output)


def _osx_create_ca_bundle(settings, destination):
    """
    Uses the OS X `security` command line tool to export the system's list of
    CA certs from /System/Library/Keychains/SystemRootCertificates.keychain.
    Checks the cert names against the trust preferences, ensuring that
    distrusted certs are not exported.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param destination:
        The full filesystem path to the destination .ca-bundle file
    """

    distrusted_certs = _osx_get_distrusted_certs(settings)

    # Export the root certs
    args = ['/usr/bin/security', 'export', '-k',
        '/System/Library/Keychains/SystemRootCertificates.keychain', '-t',
        'certs', '-p']
    result = Cli(None, settings.get('debug')).execute(args, '/usr/bin')

    certs = []
    temp = []

    in_block = False
    for line in result.splitlines():
        if line.find('BEGIN CERTIFICATE') != -1:
            in_block = True

        if in_block:
            temp.append(line)

        if line.find('END CERTIFICATE') != -1:
            in_block = False
            cert = u"\n".join(temp)
            temp = []

            if distrusted_certs:
                # If it is a distrusted cert, we move on to the next
                cert_name = openssl_get_cert_name(settings, cert)
                if cert_name in distrusted_certs:
                    if settings.get('debug'):
                        console_write(u'Skipping root certficate %s because it is distrusted' % cert_name, True)
                    continue

            certs.append(cert)

    with open_compat(destination, 'w') as f:
        f.write(u"\n".join(certs))


def _osx_get_distrusted_certs(settings):
    """
    Uses the OS X `security` binary to get a list of admin trust settings,
    which is what is set when a user changes the trust setting on a root
    certificate. By looking at the SSL policy, we can properly exclude
    distrusted certs from out export.

    Tested on OS X 10.6 and 10.8

    :param settings:
        A dict to look in for `debug` key

    :return:
        A list of CA cert names, where the name is the commonName (if
        available), or the first organizationalUnitName
    """

    args = ['/usr/bin/security', 'dump-trust-settings', '-d']
    result = Cli(None, settings.get('debug')).execute(args, '/usr/bin')

    distrusted_certs = []
    cert_name = None
    ssl_policy = False
    for line in result.splitlines():
        if line == '':
            continue

        # Reset for each cert
        match = re.match('Cert\s+\d+:\s+(.*)$', line)
        if match:
            cert_name = match.group(1)
            continue

        # Reset for each trust setting
        if re.match('^\s+Trust\s+Setting\s+\d+:', line):
            ssl_policy = False
            continue

        # We are only interested in SSL policies
        if re.match('^\s+Policy\s+OID\s+:\s+SSL', line):
            ssl_policy = True
            continue

        distrusted = re.match('^\s+Result\s+Type\s+:\s+kSecTrustSettingsResultDeny', line)
        if ssl_policy and distrusted and cert_name not in distrusted_certs:
            if settings.get('debug'):
                console_write(u'Found SSL distrust setting for root certificate %s' % cert_name, True)
            distrusted_certs.append(cert_name)

    return distrusted_certs


class OpensslCli(Cli):

    cli_name = 'openssl'

    def retrieve_binary(self):
        """
        Returns the path to the openssl executable

        :return: The string path to the executable or False on error
        """

        name = 'openssl'
        if os.name == 'nt':
            name += '.exe'

        binary = self.find_binary(name)
        if binary and os.path.isdir(binary):
            full_path = os.path.join(binary, name)
            if os.path.exists(full_path):
                binary = full_path

        if not binary:
            show_error((u'Unable to find %s. Please set the openssl_binary ' +
                u'setting by accessing the Preferences > Package Settings > ' +
                u'Package Control > Settings \u2013 User menu entry. The ' +
                u'Settings \u2013 Default entry can be used for reference, ' +
                u'but changes to that will be overwritten upon next upgrade.') % name)
            return False

        return binary
