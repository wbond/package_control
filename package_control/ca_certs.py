import hashlib
import os
import re
import time
import sys
import struct
import locale
import datetime
import platform
import base64

if os.name == 'nt':
    import ctypes
    from ctypes import windll, wintypes, POINTER, Structure, GetLastError, FormatError, sizeof
    crypt32 = windll.crypt32

from .cmd import Cli
from .console_write import console_write
from .open_compat import open_compat, read_compat
from .unicode import unicode_from_os
from .http.x509 import parse_subject, parse

try:
    str_cls = unicode
except (NameError):
    str_cls = str


# Have somewhere to store the CA bundle, even when not running in Sublime Text
try:
    import sublime
    ca_bundle_dir = None
except (ImportError):
    ca_bundle_dir = os.path.join(os.path.expanduser('~'), '.package_control')


def get_ca_bundle_path(settings):
    """
    Return the path to the merged system and user ca bundles

    :param settings:
        A dict to look in for the `debug` key

    :return:
        The filesystem path to the merged ca bundle path
    """

    ensure_ca_bundle_dir()

    system_ca_bundle_path = get_system_ca_bundle_path(settings)
    user_ca_bundle_path = get_user_ca_bundle_path(settings)
    merged_ca_bundle_path = os.path.join(ca_bundle_dir, 'Package Control.merged-ca-bundle')

    merged_missing = not os.path.exists(merged_ca_bundle_path)

    regenerate = merged_missing
    if system_ca_bundle_path and not merged_missing:
        regenerate = regenerate or os.path.getmtime(system_ca_bundle_path) > os.path.getmtime(merged_ca_bundle_path)
    if os.path.exists(user_ca_bundle_path) and not merged_missing:
        regenerate = regenerate or os.path.getmtime(user_ca_bundle_path) > os.path.getmtime(merged_ca_bundle_path)

    if regenerate:
        with open(merged_ca_bundle_path, 'wb') as merged:
            if system_ca_bundle_path:
                with open_compat(system_ca_bundle_path, 'r') as system:
                    system_certs = read_compat(system).strip()
                    merged.write(system_certs.encode('utf-8'))
                    if len(system_certs) > 0:
                        merged.write(b'\n')
            with open_compat(user_ca_bundle_path, 'r') as user:
                user_certs = read_compat(user).strip()
                merged.write(user_certs.encode('utf-8'))
                if len(user_certs) > 0:
                    merged.write(b'\n')
        if settings.get('debug'):
            console_write(u"Regnerated the merged CA bundle from the system and user CA bundles", True)

    return merged_ca_bundle_path


def get_user_ca_bundle_path(settings):
    """
    Return the path to the user CA bundle, ensuring the file exists

    :param settings:
        A dict to look in for `debug`

    :return:
        The filesystem path to the user ca bundle
    """

    ensure_ca_bundle_dir()

    user_ca_bundle_path = os.path.join(ca_bundle_dir, 'Package Control.user-ca-bundle')
    if not os.path.exists(user_ca_bundle_path):
        if settings.get('debug'):
            console_write(u"Created blank user CA bundle", True)
        open(user_ca_bundle_path, 'a').close()

    return user_ca_bundle_path


def get_system_ca_bundle_path(settings):
    """
    Get the filesystem path to the system CA bundle. On Linux it looks in a
    number of predefined places, however on OS X it has to be programatically
    exported from the SystemRootCertificates.keychain. Windows does not ship
    with a CA bundle, but also we use WinINet on Windows, so we don't need to
    worry about CA certs.

    :param settings:
        A dict to look in for the `debug` key

    :return:
        The full filesystem path to the .ca-bundle file, or False on error
    """

    platform = sys.platform
    debug = settings.get('debug')

    ca_path = False

    if platform == 'win32' or platform == 'darwin':
        ensure_ca_bundle_dir()
        ca_path = os.path.join(ca_bundle_dir, 'Package Control.system-ca-bundle')

        exists = os.path.exists(ca_path)
        # The bundle is old if it is a week or more out of date
        is_old = exists and os.stat(ca_path).st_mtime < time.time() - 604800

        if not exists or is_old:
            if platform == 'darwin':
                if debug:
                    console_write(u"Generating new CA bundle from system keychain", True)
                _osx_create_ca_bundle(settings, ca_path)
            elif platform == 'win32':
                if debug:
                    console_write(u"Generating new CA bundle from system certificate store", True)
                _win_create_ca_bundle(settings, ca_path)

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
            '/etc/ssl/certs/ca-bundle.crt',
            '/etc/pki/tls/certs/ca-bundle.crt',
            '/etc/ssl/ca-bundle.pem',
            '/usr/local/share/certs/ca-root-nss.crt',
            '/etc/ssl/cert.pem'
        ]
        # First try SSL_CERT_FILE
        if 'SSL_CERT_FILE' in os.environ:
            paths.insert(0, os.environ['SSL_CERT_FILE'])
        for path in paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                ca_path = path
                break

        if debug and ca_path:
            console_write(u"Found system CA bundle at %s" % ca_path, True)

    return ca_path


def ensure_ca_bundle_dir():
    """
    Make sure we have a placed to save the merged-ca-bundle and system-ca-bundle
    """

    # If the sublime module is available, we bind this value at run time
    # since the sublime.packages_path() is not available at import time
    global ca_bundle_dir

    if not ca_bundle_dir:
        ca_bundle_dir = os.path.join(sublime.packages_path(), 'User')
    if not os.path.exists(ca_bundle_dir):
        os.mkdir(ca_bundle_dir)


def _osx_create_ca_bundle(settings, destination):
    """
    Uses the OS X `security` command line tool to export the system's list of
    CA certs from /System/Library/Keychains/SystemRootCertificates.keychain.
    Checks the cert names against the trust preferences, ensuring that
    distrusted certs are not exported.

    :param settings:
        A dict to look in for the `debug` key

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

    debug = settings.get('debug')
    now = datetime.datetime.utcnow()

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

            base64_cert = u''.join(cert.splitlines()[1:-1])
            der_cert = base64.b64decode(base64_cert.encode('utf-8'))
            cert_info = parse(der_cert)
            subject = cert_info['subject']

            name = None
            if 'commonName' in subject:
                name = subject['commonName']
            elif 'organizationalUnitName' in subject:
                name = subject['organizationalUnitName']
            else:
                name = subject['organizationName']

            # OS X uses the first element for a repeated entry
            if isinstance(name, list):
                name = name[0]

            if cert_info['notBefore'] > now:
                if debug:
                    console_write(u'Skipping certificate "%s" since it is not valid yet' % name, True)
                continue

            if cert_info['notAfter'] < now:
                if debug:
                    console_write(u'Skipping certificate "%s" since it is no longer valid' % name, True)
                continue

            if cert_info['algorithm'] in ['md5WithRSAEncryption', 'md2WithRSAEncryption']:
                if debug:
                    console_write(u'Skipping certificate "%s" since it uses the signature algorithm %s' % (name, cert_info['algorithm']), True)
                continue

            if distrusted_certs:
                # If it is a distrusted cert, we move on to the next
                if name in distrusted_certs:
                    if settings.get('debug'):
                        console_write(u'Skipping certificate "%s" because it is distrusted' % name, True)
                    continue

            if debug:
                console_write(u'Exported certificate "%s"' % name, True)

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
                console_write(u'Found SSL distrust setting for certificate "%s"' % cert_name, True)
            distrusted_certs.append(cert_name)

    return distrusted_certs


def _win_create_ca_bundle(settings, destination):
    debug = settings.get('debug')

    certs = []

    now = datetime.datetime.utcnow()

    for store in [u"ROOT", u"CA"]:
        store_handle = crypt32.CertOpenSystemStoreW(None, store)

        if not store_handle:
            console_write(u"Error opening system certificate store %s: %s" % (store, extract_error()), True)
            continue

        cert_pointer = crypt32.CertEnumCertificatesInStore(store_handle, None)
        while bool(cert_pointer):
            context = cert_pointer.contents

            skip = False

            if context.dwCertEncodingType != X509_ASN_ENCODING:
                skip = True
                if debug:
                    console_write(u'Skipping certificate since it is not x509 encoded', True)

            if not skip:
                cert_info = context.pCertInfo.contents

                subject_struct = cert_info.Subject

                subject_length = subject_struct.cbData
                subject_bytes = ctypes.create_string_buffer(subject_length)
                ctypes.memmove(ctypes.addressof(subject_bytes), subject_struct.pbData, subject_length)

                subject = parse_subject(subject_bytes.raw[:subject_length])

                name = None
                if 'commonName' in subject:
                    name = subject['commonName']
                if not name and 'organizationalUnitName' in subject:
                    name = subject['organizationalUnitName']

                # On Windows, only the last of a key is used
                if isinstance(name, list):
                    name = name[-1]

                not_before = convert_filetime_to_datetime(cert_info.NotBefore)
                not_after  = convert_filetime_to_datetime(cert_info.NotAfter)

                if not_before > now:
                    if debug:
                        console_write(u'Skipping certificate "%s" since it is not valid yet' % name, True)
                    skip = True

            if not skip:
                if not_after < now:
                    if debug:
                        console_write(u'Skipping certificate "%s" since it is no longer valid' % name, True)
                    skip = True

            if not skip:
                cert_length = context.cbCertEncoded
                data = ctypes.create_string_buffer(cert_length)
                ctypes.memmove(ctypes.addressof(data), context.pbCertEncoded, cert_length)

                details = parse(data.raw[:cert_length])
                if details['algorithm'] in ['md5WithRSAEncryption', 'md2WithRSAEncryption']:
                    if debug:
                        console_write(u'Skipping certificate "%s" since it uses the signature algorithm %s' % (name, details['algorithm']), True)
                    skip = True

            if not skip:
                output_size = wintypes.DWORD()

                result = crypt32.CryptBinaryToStringW(ctypes.cast(data, PByte), cert_length,
                    CRYPT_STRING_BASE64HEADER | CRYPT_STRING_NOCR, None,
                    ctypes.byref(output_size))
                length = output_size.value

                if not result:
                    console_write(u'Error determining certificate size for "%s"' % name, True)
                    skip = True

            if not skip:
                buffer = ctypes.create_unicode_buffer(length)
                output_size = wintypes.DWORD(length)

                result = crypt32.CryptBinaryToStringW(ctypes.cast(data, PByte), cert_length,
                    CRYPT_STRING_BASE64HEADER | CRYPT_STRING_NOCR, buffer,
                    ctypes.byref(output_size))
                output = buffer.value

                if debug:
                    console_write(u'Exported certificate "%s"' % name, True)

                certs.append(output.strip())

            cert_pointer = crypt32.CertEnumCertificatesInStore(store_handle, cert_pointer)

        result = crypt32.CertCloseStore(store_handle, 0)
        store_handle = None
        if not result:
            console_write(u'Error closing certificate store "%s"' % store, True)

    with open_compat(destination, 'w') as f:
        f.write(u"\n".join(certs))


if os.name == 'nt':
    # Constants from wincrypt.h
    X509_ASN_ENCODING = 1
    CRYPT_STRING_BASE64HEADER = 0
    CRYPT_STRING_NOCR = 0x80000000


    def extract_error():
        error_num = GetLastError()
        error_string = FormatError(error_num)
        return unicode_from_os(error_string)


    PByte = POINTER(wintypes.BYTE)
    class CryptBlob(Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", PByte)
        ]


    class CryptAlgorithmIdentifier(Structure):
        _fields_ = [
            ("pszObjId", wintypes.LPSTR),
            ("Parameters", CryptBlob)
        ]


    class FileTime(Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD)
        ]


    class CertPublicKeyInfo(Structure):
        _fields_ = [
            ("Algorithm", CryptAlgorithmIdentifier),
            ("PublicKey", CryptBlob)
        ]


    class CertExtension(Structure):
        _fields_ = [
            ("pszObjId", wintypes.LPSTR),
            ("fCritical", wintypes.BOOL),
            ("Value", CryptBlob)
        ]
    PCertExtension = POINTER(CertExtension)


    class CertInfo(Structure):
        _fields_ = [
            ("dwVersion", wintypes.DWORD),
            ("SerialNumber", CryptBlob),
            ("SignatureAlgorithm", CryptAlgorithmIdentifier),
            ("Issuer", CryptBlob),
            ("NotBefore", FileTime),
            ("NotAfter", FileTime),
            ("Subject", CryptBlob),
            ("SubjectPublicKeyInfo", CertPublicKeyInfo),
            ("IssuerUniqueId", CryptBlob),
            ("SubjectUniqueId", CryptBlob),
            ("cExtension", wintypes.DWORD),
            ("rgExtension", POINTER(PCertExtension))
        ]
    PCertInfo = POINTER(CertInfo)


    class CertContext(Structure):
        _fields_ = [
            ("dwCertEncodingType", wintypes.DWORD),
            ("pbCertEncoded", PByte),
            ("cbCertEncoded", wintypes.DWORD),
            ("pCertInfo", PCertInfo),
            ("hCertStore", wintypes.HANDLE)
        ]
    PCertContext = POINTER(CertContext)


    crypt32.CertOpenSystemStoreW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR]
    crypt32.CertOpenSystemStoreW.restype = wintypes.HANDLE
    crypt32.CertEnumCertificatesInStore.argtypes = [wintypes.HANDLE, PCertContext]
    crypt32.CertEnumCertificatesInStore.restype = PCertContext
    crypt32.CertCloseStore.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    crypt32.CertCloseStore.restype = wintypes.BOOL
    crypt32.CryptBinaryToStringW.argtypes = [PByte, wintypes.DWORD, wintypes.DWORD, wintypes.LPWSTR, POINTER(wintypes.DWORD)]
    crypt32.CryptBinaryToStringW.restype = wintypes.BOOL


    def convert_filetime_to_datetime(filetime):
        """
        Windows returns times as 64-bit unsigned longs that are the number
        of hundreds of nanoseconds since Jan 1 1601. This converts it to
        a datetime object.

        :param filetime:
            A FileTime struct object

        :return:
            A (UTC) datetime object
        """

        hundreds_nano_seconds = struct.unpack('>Q', struct.pack('>LL', filetime.dwHighDateTime, filetime.dwLowDateTime))[0]
        seconds_since_1601 = hundreds_nano_seconds / 10000000
        epoch_seconds = seconds_since_1601 - 11644473600 # Seconds from Jan 1 1601 to Jan 1 1970
        return datetime.datetime.fromtimestamp(epoch_seconds)
