import os
import sublime
import sys

try:
    # python 3.8+
    from importlib import reload
except ImportError:
    # python 3.3
    from imp import reload

# reload already registered sub modules
for suffix in (
    '',

    '.sys_path',
    '.settings',
    '.text',
    '.activity_indicator',
    '.console_write',
    '.show_error',

    '.cache',
    '.http_cache',
    '.clear_directory',

    '.pep440',
    '.pep508',
    '.distinfo',
    '.library',

    '.cmd',
    '.processes',

    '.deps.semver',
    '.package_version',
    '.selectors',

    '.deps.asn1crypto._errors',
    '.deps.asn1crypto._int',
    '.deps.asn1crypto._ordereddict',
    '.deps.asn1crypto._teletex_codec',
    '.deps.asn1crypto._types',
    '.deps.asn1crypto._inet',
    '.deps.asn1crypto._iri',
    '.deps.asn1crypto.version',
    '.deps.asn1crypto.pem',
    '.deps.asn1crypto.util',
    '.deps.asn1crypto.parser',
    '.deps.asn1crypto.core',
    '.deps.asn1crypto.algos',
    '.deps.asn1crypto.keys',
    '.deps.asn1crypto.x509',
    '.deps.asn1crypto.crl',
    '.deps.asn1crypto.csr',
    '.deps.asn1crypto.ocsp',
    '.deps.asn1crypto.cms',
    '.deps.asn1crypto.pdf',
    '.deps.asn1crypto.pkcs12',
    '.deps.asn1crypto.tsp',
    '.deps.asn1crypto',

    '.deps.oscrypto._asn1',
    '.deps.oscrypto._cipher_suites',
    '.deps.oscrypto._errors',
    '.deps.oscrypto._int',
    '.deps.oscrypto._types',
    '.deps.oscrypto.errors',
    '.deps.oscrypto.version',
    '.deps.oscrypto',
    '.deps.oscrypto._ffi',
    '.deps.oscrypto._pkcs12',
    '.deps.oscrypto._pkcs5',
    '.deps.oscrypto._rand',
    '.deps.oscrypto._tls',
    '.deps.oscrypto._linux_bsd.trust_list',
    '.deps.oscrypto._mac._common_crypto_cffi',
    '.deps.oscrypto._mac._common_crypto_ctypes',
    '.deps.oscrypto._mac._common_crypto',
    '.deps.oscrypto._mac._core_foundation_cffi',
    '.deps.oscrypto._mac._core_foundation_ctypes',
    '.deps.oscrypto._mac._core_foundation',
    '.deps.oscrypto._mac._security_cffi',
    '.deps.oscrypto._mac._security_ctypes',
    '.deps.oscrypto._mac._security',
    '.deps.oscrypto._mac.trust_list',
    '.deps.oscrypto._mac.util',
    '.deps.oscrypto._openssl._libcrypto_cffi',
    '.deps.oscrypto._openssl._libcrypto_ctypes',
    '.deps.oscrypto._openssl._libcrypto',
    '.deps.oscrypto._openssl._libssl_cffi',
    '.deps.oscrypto._openssl._libssl_ctypes',
    '.deps.oscrypto._openssl._libssl',
    '.deps.oscrypto._openssl.util',
    '.deps.oscrypto._win._cng_cffi',
    '.deps.oscrypto._win._cng_ctypes',
    '.deps.oscrypto._win._cng',
    '.deps.oscrypto._win._decode',
    '.deps.oscrypto._win._advapi32_cffi',
    '.deps.oscrypto._win._advapi32_ctypes',
    '.deps.oscrypto._win._advapi32',
    '.deps.oscrypto._win._kernel32_cffi',
    '.deps.oscrypto._win._kernel32_ctypes',
    '.deps.oscrypto._win._kernel32',
    '.deps.oscrypto._win._secur32_cffi',
    '.deps.oscrypto._win._secur32_ctypes',
    '.deps.oscrypto._win._secur32',
    '.deps.oscrypto._win._crypt32_cffi',
    '.deps.oscrypto._win._crypt32_ctypes',
    '.deps.oscrypto._win._crypt32',
    '.deps.oscrypto._win.trust_list',
    '.deps.oscrypto._win.util',
    '.deps.oscrypto.trust_list',
    '.deps.oscrypto.util',
    '.deps.oscrypto.kdf',
    '.deps.oscrypto._mac.symmetric',
    '.deps.oscrypto._openssl.symmetric',
    '.deps.oscrypto._win.symmetric',
    '.deps.oscrypto.symmetric',
    '.deps.oscrypto._asymmetric',
    '.deps.oscrypto._ecdsa',
    '.deps.oscrypto._pkcs1',
    '.deps.oscrypto._mac.asymmetric',
    '.deps.oscrypto._openssl.asymmetric',
    '.deps.oscrypto._win.asymmetric',
    '.deps.oscrypto.asymmetric',
    '.deps.oscrypto.keys',
    '.deps.oscrypto._mac.tls',
    '.deps.oscrypto._openssl.tls',
    '.deps.oscrypto._win.tls',
    '.deps.oscrypto.tls',

    '.http',
    '.http.invalid_certificate_exception',
    '.http.debuggable_http_response',
    '.http.debuggable_https_response',
    '.http.debuggable_http_connection',
    '.http.persistent_handler',
    '.http.debuggable_http_handler',
    '.http.validating_https_connection',
    '.http.validating_https_handler',

    '.ca_certs',

    '.downloaders.downloader_exception',
    '.downloaders.rate_limit_exception',
    '.downloaders.binary_not_found_error',
    '.downloaders.non_clean_exit_error',
    '.downloaders.non_http_error',
    '.downloaders.basic_auth_downloader',
    '.downloaders.caching_downloader',
    '.downloaders.decoding_downloader',
    '.downloaders.limiting_downloader',
    '.downloaders.urllib_downloader',
    '.downloaders.cli_downloader',
    '.downloaders.curl_downloader',
    '.downloaders.wget_downloader',
    '.downloaders.win_downloader_exception',
    '.downloaders.wininet_downloader',
    '.downloaders.oscrypto_downloader_exception',
    '.downloaders.oscrypto_downloader',
    '.downloaders',

    '.download_manager',

    '.clients',
    '.clients.client_exception',
    '.clients.json_api_client',
    '.clients.bitbucket_client',
    '.clients.github_client',
    '.clients.gitlab_client',
    '.clients.readme_client',

    '.providers.base_repository_provider',
    '.providers.provider_exception',
    '.providers.bitbucket_repository_provider',
    '.providers.github_repository_provider',
    '.providers.github_user_provider',
    '.providers.gitlab_repository_provider',
    '.providers.gitlab_user_provider',
    '.providers.schema_version',
    '.providers.channel_provider',
    '.providers.repository_provider',
    '.providers',

    '.upgraders',
    '.upgraders.vcs_upgrader',
    '.upgraders.git_upgrader',
    '.upgraders.hg_upgrader',

    '.package_io',
    '.package_manager',
    '.package_creator',
    '.package_disabler',
    '.package_tasks',

    '.tests',
    '.tests.downloaders',
    '.tests.clients',
    '.tests.providers',

    '.commands.add_channel_command',
    '.commands.add_repository_command',
    '.commands.create_package_command',
    '.commands.disable_package_command',
    '.commands.disable_packages_command',
    '.commands.discover_packages_command',
    '.commands.enable_package_command',
    '.commands.enable_packages_command',
    '.commands.existing_packages_command',
    '.commands.install_package_command',
    '.commands.install_packages_command',
    '.commands.list_packages_command',
    '.commands.list_unmanaged_packages_command',
    '.commands.new_template_command',
    '.commands.remove_channel_command',
    '.commands.remove_package_command',
    '.commands.remove_packages_command',
    '.commands.remove_repository_command',
    '.commands.upgrade_all_packages_command',
    '.commands.upgrade_package_command',
    '.commands.satisfy_libraries_command',
    '.commands.satisfy_packages_command',
    '.commands.package_control_edit_settings_command',
    '.commands.package_control_disable_debug_mode_command',
    '.commands.package_control_enable_debug_mode_command',
    '.commands.package_control_insert_command',
    '.commands.package_control_message_command',
    '.commands.package_control_tests_command',
    '.commands',

    '.automatic_upgrader',
    '.package_cleanup',
    '.bootstrap'
):
    mod = 'Package Control.package_control' + suffix
    if mod in sys.modules:
        try:
            reload(sys.modules[mod])
        except (ImportError, FileNotFoundError):
            pass  # Upgrade issues from PC 2.0 -> 3.0

from .package_control.package_io import (
    get_installed_package_path,
    get_package_dir,
    regular_file_exists
)
from .package_control import text

has_packed = os.path.exists(get_installed_package_path('Package Control'))
has_unpacked = regular_file_exists('Package Control', 'plugin.py')

# Ensure least requires ST version
if int(sublime.version()) < 3143:
    message = text.format(
        '''
        Package Control

        This package requires at least Sublime Text 3143.

        Please consider updating ST or remove Package Control.
        '''
    )
    sublime.error_message(message)

    def plugin_loaded():
        """
        plugin loaded hook

        Disable Package Control to avoid error message popping up again.
        """

        from .package_control.bootstrap import disable_package_control
        disable_package_control()

# Ensure the user has installed Package Control properly
elif __package__ != 'Package Control':
    message = text.format(
        '''
        Package Control

        This package appears to be installed incorrectly.

        It should be installed as "Package Control", but seems to be installed
        as "%s".

        To fix the issue, please:

        1. Open the "Preferences" menu
        2. Select "Browse Packages\u2026"
        ''',
        __package__,
        strip=False
    )

    # If installed unpacked
    if os.path.exists(get_package_dir(__package__)):
        message += text.format(
            '''
            3. Rename the folder "%s" to "Package Control"
            4. Restart Sublime Text
            ''',
            __package__
        )
    # If installed as a .sublime-package file
    else:
        message += text.format(
            '''
            3. Browse up a folder
            4. Browse into the "Installed Packages/" folder
            5. Rename "%s.sublime-package" to "Package Control.sublime-package"
            6. Restart Sublime Text
            ''',
            __package__
        )
    sublime.error_message(message)

elif has_packed and has_unpacked:
    message = text.format(
        '''
        Package Control

        It appears you have Package Control installed as both a
        .sublime-package file and a directory inside of the Packages folder.

        To fix this issue, please:

        1. Open the "Preferences" menu
        2. Select "Browse Packages\u2026"
        3. Delete the folder "Package Control"
        4. Restart Sublime Text
        '''
    )
    sublime.error_message(message)

else:
    # Make sure the user's locale can handle non-ASCII. A whole bunch of
    # work was done to try and make Package Control work even if the locale
    # was poorly set, by manually encoding all file paths, but it ended up
    # being a fool's errand since the package loading code built into
    # Sublime Text is not written to work that way, and although packages
    # could be installed, they could not be loaded properly.
    try:
        os.path.exists(get_package_dir("fran\u2013ais"))
    except (UnicodeEncodeError) as exception:
        message = text.format(
            '''
            Package Control

            Your system's locale is set to a value that can not handle
            non-ASCII characters. Package Control can not properly work
            unless this is fixed.

            On Linux, please reference your distribution's docs for
            information on properly setting the LANG and LC_CTYPE
            environmental variables. As a temporary work-around, you can
            launch Sublime Text from the terminal with:

              LANG=en_US.UTF-8 LC_CTYPE=en_US.UTF-8 sublime_text

            Error Details:

              %s
            ''',
            exception,
            strip=False
        )
        sublime.error_message(message)

    # Normal execution will finish setting up the package
    else:
        from .package_control.commands import *  # noqa

        def plugin_loaded():
            """
            Run bootstrapping once plugin is loaded

            Bootstrapping is executed with little delay to work around a ST core bug,
            which causes `sublime.load_resource()` to fail when being called directly
            by `bootstrap()` hook.
            """

            from .package_control.bootstrap import bootstrap
            bootstrap()
