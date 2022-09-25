import os
import time
import sys

from . import sys_path
from .console_write import console_write

try:
    import certifi
except ImportError:
    certifi = None

try:
    from .deps.oscrypto import use_ctypes
    use_ctypes()
    from .deps.oscrypto import trust_list  # noqa
except Exception as e:
    trust_list = None
    console_write('oscrypto trust lists unavailable - %s', e)


def get_ca_bundle_path(settings):
    """
    Return the path to the merged system and user ca bundles

    :param settings:
        A dict to look in for the `debug` key

    :return:
        The filesystem path to the merged ca bundle path
    """

    ca_bundle_dir = sys_path.pc_cache_dir()
    if not ca_bundle_dir:
        raise ValueError("Unknown Package Control cache directory")

    os.makedirs(ca_bundle_dir, exist_ok=True)

    system_ca_bundle_path = get_system_ca_bundle_path(settings, ca_bundle_dir)
    user_ca_bundle_path = get_user_ca_bundle_path(settings)
    merged_ca_bundle_path = os.path.join(ca_bundle_dir, 'merged-ca-bundle.crt')

    merged_missing = not os.path.exists(merged_ca_bundle_path)
    merged_empty = (not merged_missing) and os.stat(merged_ca_bundle_path).st_size == 0

    regenerate = merged_missing or merged_empty
    if system_ca_bundle_path and not merged_missing:
        regenerate = regenerate or os.path.getmtime(system_ca_bundle_path) > os.path.getmtime(merged_ca_bundle_path)
    if os.path.exists(user_ca_bundle_path) and not merged_missing:
        regenerate = regenerate or os.path.getmtime(user_ca_bundle_path) > os.path.getmtime(merged_ca_bundle_path)

    if regenerate:
        with open(merged_ca_bundle_path, 'w', encoding='utf-8') as merged:
            if system_ca_bundle_path:
                with open(system_ca_bundle_path, 'r', encoding='utf-8') as system:
                    system_certs = system.read().strip()
                    merged.write(system_certs)
                    if len(system_certs) > 0:
                        merged.write('\n')
            if os.path.exists(user_ca_bundle_path):
                with open(user_ca_bundle_path, 'r', encoding='utf-8') as user:
                    user_certs = user.read().strip()
                    merged.write(user_certs)
                    if len(user_certs) > 0:
                        merged.write('\n')
        if settings.get('debug'):
            console_write(
                '''
                Regenerated the merged CA bundle from the system and user CA bundles
                '''
            )

    return merged_ca_bundle_path


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
            '''
            Exported certificate: %s
            ''',
            cert.subject.human_friendly
        )
    else:
        console_write(
            '''
            Skipped certificate: %s - reason %s
            ''',
            (cert.subject.human_friendly, reason)
        )


def get_system_ca_bundle_path(settings, ca_bundle_dir):
    """
    Get the filesystem path to the system CA bundle. On Linux it looks in a
    number of predefined places, however on OS X it has to be programatically
    exported from the SystemRootCertificates.keychain. Windows does not ship
    with a CA bundle, but also we use WinINet on Windows, so we don't need to
    worry about CA certs.

    :param settings:
        A dict to look in for the `debug` key

    :param ca_bundle_dir:
        The filesystem path to the directory to store exported CA bundle in

    :return:
        The full filesystem path to the .ca-bundle file, or False on error
    """

    hours_to_cache = 7 * 24

    debug = settings.get('debug')

    ca_path = False

    if sys.platform == 'win32' or sys.platform == 'darwin':
        if trust_list is not None:
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
                cert_callback = None
                if debug:
                    console_write(
                        '''
                        Generating new CA bundle from system keychain
                        '''
                    )
                    cert_callback = print_cert_subject
                trust_list.get_path(ca_bundle_dir, hours_to_cache, cert_callback=cert_callback)
                if debug:
                    console_write(
                        '''
                        Finished generating new CA bundle at %s (%d bytes)
                        ''',
                        (ca_path, os.stat(ca_path).st_size)
                    )

            elif debug:
                console_write(
                    '''
                    Found previously exported CA bundle at %s (%d bytes)
                    ''',
                    (ca_path, os.stat(ca_path).st_size)
                )

        elif debug:
            console_write(
                '''
                Can't export system CA - oscrypto not available!
                ''',
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
                '''
                Found system CA bundle at %s (%d bytes)
                ''',
                (ca_path, os.stat(ca_path).st_size)
            )

    if not ca_path:
        if certifi is not None:
            ca_path = certifi.where()
            if debug:
                console_write(
                    '''
                    No system CA bundle found in one of the expected locations -
                    using certifi %s instead.
                    ''',
                    certifi.__version__
                )

        else:
            console_write(
                '''
                No system CA bundle found in one of the expected locations!
                '''
            )

    return ca_path


def get_user_ca_bundle_path(settings):
    """
    Return the path to the user CA bundle, ensuring the file exists

    :param settings:
        A dict to look in for `debug`

    :return:
        The full filesystem path to the .user-ca-bundle file, or False on error
    """

    user_ca_bundle = os.path.join(sys_path.user_config_dir(), 'Package Control.user-ca-bundle')
    try:
        open(user_ca_bundle, 'xb').close()
        if settings.get('debug'):
            console_write('Created blank user CA bundle')
    except FileExistsError:
        pass
    except OSError as e:
        user_ca_bundle = False
        if settings.get('debug'):
            console_write('Unable to create blank user CA bundle - %s', e)

    return user_ca_bundle
