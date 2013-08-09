import sys

import sublime


st_version = 2
# With the way ST3 works, the sublime module is not "available" at startup
# which results in an empty version number
if sublime.version() == '' or int(sublime.version()) > 3000:
    st_version = 3
    from imp import reload


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
    if mod[0:15].lower().replace(' ', '_') == 'package_control' and sys.modules[mod] != None:
        reload_mods.append(mod)

mod_prefix = 'package_control'
if st_version == 3:
    mod_prefix = 'Package Control.' + mod_prefix

mods_load_order = [
    '',

    '.sys_path',
    '.cache',
    '.http_cache',
    '.ca_certs',
    '.clear_directory',
    '.cmd',
    '.console_write',
    '.preferences_filename',
    '.show_error',
    '.unicode',
    '.thread_progress',
    '.package_io',
    '.semver',
    '.versions',

    '.http',
    '.http.invalid_certificate_exception',
    '.http.debuggable_http_response',
    '.http.debuggable_https_response',
    '.http.debuggable_http_connection',
    '.http.persistent_handler',
    '.http.debuggable_http_handler',
    '.http.validating_https_connection',
    '.http.validating_https_handler',

    '.clients',
    '.clients.client_exception',
    '.clients.bitbucket_client',
    '.clients.github_client',
    '.clients.readme_client',
    '.clients.json_api_client',

    '.providers',
    '.providers.provider_exception',
    '.providers.bitbucket_repository_provider',
    '.providers.channel_provider',
    '.providers.github_repository_provider',
    '.providers.github_user_provider',
    '.providers.repository_provider',
    '.providers.release_selector',

    '.download_manager',

    '.downloaders',
    '.downloaders.downloader_exception',
    '.downloaders.rate_limit_exception',
    '.downloaders.binary_not_found_error',
    '.downloaders.non_clean_exit_error',
    '.downloaders.non_http_error',
    '.downloaders.caching_downloader',
    '.downloaders.decoding_downloader',
    '.downloaders.limiting_downloader',
    '.downloaders.cert_provider',
    '.downloaders.urllib_downloader',
    '.downloaders.cli_downloader',
    '.downloaders.curl_downloader',
    '.downloaders.wget_downloader',
    '.downloaders.wininet_downloader',
    '.downloaders.background_downloader',

    '.upgraders',
    '.upgraders.vcs_upgrader',
    '.upgraders.git_upgrader',
    '.upgraders.hg_upgrader',

    '.package_manager',
    '.package_creator',
    '.package_installer',
    '.package_renamer',

    '.commands',
    '.commands.add_channel_command',
    '.commands.add_repository_command',
    '.commands.create_binary_package_command',
    '.commands.create_package_command',
    '.commands.disable_package_command',
    '.commands.discover_packages_command',
    '.commands.enable_package_command',
    '.commands.existing_packages_command',
    '.commands.grab_certs_command',
    '.commands.install_package_command',
    '.commands.list_packages_command',
    '.commands.package_message_command',
    '.commands.remove_package_command',
    '.commands.upgrade_all_packages_command',
    '.commands.upgrade_package_command',

    '.package_cleanup',
    '.automatic_upgrader'
]

for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        reload(sys.modules[mod])
