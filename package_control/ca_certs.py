import os
import sys

from . import sys_path
from .console_write import console_write
from .downloaders.downloader_exception import DownloaderException

try:
    import certifi
except ImportError:
    certifi = None

try:
    from .deps.oscrypto import use_ctypes
    use_ctypes()
    from .deps.oscrypto import trust_list  # noqa
    from .deps.oscrypto.errors import CACertsError
except Exception as e:
    trust_list = None
    console_write('oscrypto trust lists unavailable - %s', e)


MIN_BUNDLE_SIZE = 100
"""
The least required file size a CA bundle must have to be valid.

The size is calculated from public key boundaries
and least amount of public key size.

``MIN_BUNDLE_SIZE = begin (27) + end (25) + newlines (2) + key (?)``

```
-----BEGIN CERTIFICATE-----
<public key content>
-----END CERTIFICATE-----
```
"""


def get_ca_bundle_path(settings):
    """
    Return the path to the merged system and user ca bundles

    :param settings:
        A dict to look in for the `debug` key

    :raises:
        OSError or IOError if CA bundle creation fails

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
    merged_ca_bundle_size = 0

    try:
        # file exists and is not empty
        system_ca_bundle_exists = system_ca_bundle_path \
            and os.path.getsize(system_ca_bundle_path) > MIN_BUNDLE_SIZE
    except FileNotFoundError:
        system_ca_bundle_exists = False

    try:
        # file exists and is not empty
        user_ca_bundle_exists = user_ca_bundle_path \
            and os.path.getsize(user_ca_bundle_path) > MIN_BUNDLE_SIZE
    except FileNotFoundError:
        user_ca_bundle_exists = False

    regenerate = system_ca_bundle_exists or user_ca_bundle_exists
    if regenerate:
        try:
            stats = os.stat(merged_ca_bundle_path)
        except FileNotFoundError:
            pass
        else:
            merged_ca_bundle_size = stats.st_size
            # regenerate if merged file is empty
            regenerate = merged_ca_bundle_size < MIN_BUNDLE_SIZE
            # regenerate if system CA file is newer
            if system_ca_bundle_exists and not regenerate:
                regenerate = os.path.getmtime(system_ca_bundle_path) > stats.st_mtime
            # regenerate if user CA file is newer
            if user_ca_bundle_exists and not regenerate:
                regenerate = os.path.getmtime(user_ca_bundle_path) > stats.st_mtime

    if regenerate:
        with open(merged_ca_bundle_path, 'w', encoding='utf-8') as merged:
            if system_ca_bundle_exists:
                with open(system_ca_bundle_path, 'r', encoding='utf-8') as system:
                    system_certs = system.read().strip()
                    merged.write(system_certs)
                    if len(system_certs) > 0:
                        merged.write('\n')
            if user_ca_bundle_exists:
                with open(user_ca_bundle_path, 'r', encoding='utf-8') as user:
                    user_certs = user.read().strip()
                    merged.write(user_certs)
                    if len(user_certs) > 0:
                        merged.write('\n')

            merged_ca_bundle_size = merged.tell()

        if merged_ca_bundle_size >= MIN_BUNDLE_SIZE and settings.get('debug'):
            console_write(
                '''
                Regenerated the merged CA bundle from the system and user CA bundles (%d kB)
                ''',
                merged_ca_bundle_size / 1024
            )

    if merged_ca_bundle_size < MIN_BUNDLE_SIZE:
        raise DownloaderException("No CA bundle available for HTTPS!")

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

            if trust_list._cached_path_needs_update(ca_path, hours_to_cache):
                cert_callback = None
                if debug:
                    console_write(
                        '''
                        Generating new CA bundle from system keychain
                        '''
                    )
                    cert_callback = print_cert_subject

                try:
                    trust_list.get_path(ca_bundle_dir, hours_to_cache, cert_callback)
                    if debug:
                        console_write(
                            '''
                            Finished generating new CA bundle at %s (%d bytes)
                            ''',
                            (ca_path, os.stat(ca_path).st_size)
                        )

                except (CACertsError, OSError) as e:
                    ca_path = False
                    if debug:
                        console_write(
                            '''
                            Failed to generate new CA bundle. %s
                            ''',
                            e
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
                Unable to generate system CA bundle - oscrypto not available!
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

        # Prepend SSL_CERT_FILE only, if it doesn't match ST4's certifi CA bundle.
        # Otherwise we'd never pick up any OS level CA bundle.
        ssl_cert_file = os.environ.get('SSL_CERT_FILE')
        if ssl_cert_file and not (certifi and os.path.samefile(ssl_cert_file, certifi.where())):
            paths.insert(0, ssl_cert_file)

        for path in paths:
            if os.path.isfile(path) and os.path.getsize(path) > MIN_BUNDLE_SIZE:
                ca_path = path
                break

        if debug:
            if ca_path:
                console_write(
                    '''
                    Found system CA bundle at %s (%d bytes)
                    ''',
                    (ca_path, os.stat(ca_path).st_size)
                )
            else:
                console_write(
                    '''
                    Failed to find system CA bundle.
                    '''
                )

    if ca_path is False and certifi is not None:
        ca_path = certifi.where()
        if debug:
            console_write(
                '''
                Using CA bundle from "certifi %s" instead.
                ''',
                certifi.__version__
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
