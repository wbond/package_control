import sys


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
    if (mod[0:16] == 'package_control.' or mod == 'package_control') and sys.modules[mod] != None:
        reload_mods.append(mod)

mods_load_order = [
    'package_control',

    'package_control.sys_path',
    'package_control.cache',
    'package_control.clear_directory',
    'package_control.cmd',
    'package_control.console_write',
    'package_control.preferences_filename',
    'package_control.show_error',
    'package_control.unicode',
    'package_control.thread_progress',

    'package_control.http',
    'package_control.http.invalid_certificate_exception',
    'package_control.http.rate_limit_exception',
    'package_control.http.proxy_ntlm_auth_handler',
    'package_control.http.debuggable_http_response',
    'package_control.http.debuggable_https_response',
    'package_control.http.debuggable_http_connection',
    'package_control.http.debuggable_http_handler',
    'package_control.http.validating_https_connection',
    'package_control.http.validating_https_handler',

    'package_control.providers',
    'package_control.providers.bitbucket_package_provider',
    'package_control.providers.channel_provider',
    'package_control.providers.datetime',
    'package_control.providers.github_package_provider',
    'package_control.providers.github_user_provider',
    'package_control.providers.non_caching_provider',
    'package_control.providers.package_provider',
    'package_control.providers.platform_comparator',

    'package_control.downloaders',
    'package_control.downloaders.binary_not_found_error',
    'package_control.downloaders.non_clean_exit_error',
    'package_control.downloaders.non_http_error',
    'package_control.downloaders.downloader',
    'package_control.downloaders.urllib2_downloader',
    'package_control.downloaders.cli_downloader',
    'package_control.downloaders.curl_downloader',
    'package_control.downloaders.wget_downloader',
    'package_control.downloaders.repository_downloader',

    'package_control.upgraders',
    'package_control.upgraders.vcs_upgrader',
    'package_control.upgraders.git_upgrader',
    'package_control.upgraders.hg_upgrader',

    'package_control.package_manager',
    'package_control.package_creator',
    'package_control.package_installer',
    'package_control.package_renamer',

    'package_control.commands',
    'package_control.commands.add_repository_channel_command',
    'package_control.commands.add_repository_command',
    'package_control.commands.create_binary_package_command',
    'package_control.commands.create_package_command',
    'package_control.commands.disable_package_command',
    'package_control.commands.discover_packages_command',
    'package_control.commands.enable_package_command',
    'package_control.commands.existing_packages_command',
    'package_control.commands.install_package_command',
    'package_control.commands.list_packages_command',
    'package_control.commands.remove_package_command',
    'package_control.commands.upgrade_all_packages_command',
    'package_control.commands.upgrade_package_command',

    'package_control.package_cleanup',
    'package_control.automatic_upgrader'
]

for mod in mods_load_order:
    if mod in reload_mods:
        reload(sys.modules[mod])
