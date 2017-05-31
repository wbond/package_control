import os
import time
import sys

from .console_write import console_write
from .open_compat import open_compat, read_compat
from .deps.oscrypto import trust_list


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
    merged_empty = (not merged_missing) and os.stat(merged_ca_bundle_path).st_size == 0

    regenerate = merged_missing or merged_empty
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
            console_write(
                u'''
                Regenerated the merged CA bundle from the system and user CA bundles
                '''
            )

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
            console_write(
                u'''
                Created blank user CA bundle
                '''
            )
        open(user_ca_bundle_path, 'a').close()

    return user_ca_bundle_path


def print_cert_subject(cert, reason):
    """
    :param cert:
        The asn1crypto.x509.Certificate object

    :param reason:
        None if being exported, or a unicode string of the reason not being
        exported
    """

    if reason is None:
        console_write(
            u'''
            Exported certificate: %s
            ''',
            cert.subject.human_friendly
        )
    else:
        console_write(
            u'''
            Skipped certificate: %s - reason %s
            ''',
            (cert.subject.human_friendly, reason)
        )


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

    hours_to_cache = 7 * 24

    platform = sys.platform
    debug = settings.get('debug')

    ca_path = False

    if platform == 'win32' or platform == 'darwin':
        # Remove any file with the old system bundle filename
        old_ca_path = os.path.join(ca_bundle_dir, 'Package Control.system-ca-bundle')
        if os.path.exists(old_ca_path):
            os.unlink(old_ca_path)

        ensure_ca_bundle_dir()
        ca_path, _ = trust_list._ca_path(ca_bundle_dir)

        exists = os.path.exists(ca_path)
        is_empty = False
        is_old = False
        if exists:
            stats = os.stat(ca_path)
            is_empty = stats.st_size == 0
            # The bundle is old if it is a week or more out of date
            is_old = stats.st_mtime < time.time() - (hours_to_cache * 60 * 60)

        if not exists or is_empty or is_old:
            if debug:
                console_write(
                    u'''
                    Generating new CA bundle from system keychain
                    '''
                )
            trust_list.get_path(ca_bundle_dir, hours_to_cache, cert_callback=print_cert_subject)
            if debug:
                console_write(
                    u'''
                    Finished generating new CA bundle at %s (%d bytes)
                    ''',
                    (ca_path, os.stat(ca_path).st_size)
                )

        elif debug:
            console_write(
                u'''
                Found previously exported CA bundle at %s (%d bytes)
                ''',
                (ca_path, os.stat(ca_path).st_size)
            )

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
            console_write(
                u'''
                Found system CA bundle at %s (%d bytes)
                ''',
                (ca_path, os.stat(ca_path).st_size)
            )

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
        try:
            os.mkdir(ca_bundle_dir)
        except PermissionError:
            ca_bundle_dir = '/var/tmp/package_control'
            if not os.path.exists(ca_bundle_dir):
                 os.mkdir(ca_bundle_dir)
