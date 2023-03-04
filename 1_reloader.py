import sys

try:
    # python 3.8
    from importlib import reload
except ImportError:
    # python 3.3
    from imp import reload

import sublime


st_build = int(sublime.version())
mod_prefix = 'package_control'

bare_mod_prefix = mod_prefix
mod_prefix = 'Package Control.' + mod_prefix


# Python allows reloading modules on the fly, which allows us to do live upgrades.
# The only caveat to this is that you have to reload in the dependency order.
#
# Thus is module A depends on B and we don't reload B before A, when A is reloaded
# it will still have a reference to the old B. Thus we hard-code the dependency
# order of the various Package Control modules so they get reloaded properly.
#
# There are solutions for doing this all programatically, but this is much easier
# to understand.
reload_mods = []
for mod in sys.modules:
    if mod[0:15] in set(['package_control', 'Package Control']) and sys.modules[mod] is not None:
        reload_mods.append(mod)

mods_load_order = [
    '',

    '.sys_path',
    '.distinfo',
    '.pep440',
    '.pep508',
    '.library',
    '.text',
    '.cache',
    '.http_cache',
    '.console_write',
    '.clear_directory',
    '.show_error',
    '.cmd',
    '.processes',
    '.selectors',
    '.settings',
    '.activity_indicator',
    '.package_io',
    '.deps.semver',
    '.package_version',

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
    '.downloaders.background_downloader',
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
    '.providers.schema_compat',
    '.providers.channel_provider',
    '.providers.repository_provider',
    '.providers',

    '.upgraders',
    '.upgraders.vcs_upgrader',
    '.upgraders.git_upgrader',
    '.upgraders.hg_upgrader',

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
    '.commands.remove_channel_command',
    '.commands.remove_package_command',
    '.commands.remove_packages_command',
    '.commands.remove_repository_command',
    '.commands.upgrade_all_packages_command',
    '.commands.upgrade_package_command',
    '.commands.package_control_insert_command',
    '.commands.satisfy_libraries_command',
    '.commands.package_control_tests_command',
    '.commands.package_control_edit_settings_command',
    '.commands.package_control_disable_debug_mode_command',
    '.commands.package_control_enable_debug_mode_command',
    '.commands',

    '.automatic_upgrader',
    '.package_cleanup'
]


for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        try:
            reload(sys.modules[mod])
        except (ImportError, FileNotFoundError):
            pass  # Upgrade issues from PC 2.0 -> 3.0
