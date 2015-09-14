import os
import sys
import sublime_plugin

if sys.version_info >= (3,):
    import importlib
    import zipimport


mod_prefix = 'package_control'

# ST3 loads each package as a module, so it needs an extra prefix
if sys.version_info >= (3,):
    bare_mod_prefix = mod_prefix
    mod_prefix = 'Package Control.' + mod_prefix
    from imp import reload

# When reloading the package, we also need to reload the base "package_control"
# module in ST3. This flag inidicates we should re-add the PC package path
# to the beginning of sys.path before we try to reload.
do_insert = False
is_zipped = False

commands_name = mod_prefix + '.commands'
if commands_name in sys.modules and sys.version_info >= (3,):
    # Unfortunately with ST3, the ZipLoader does not "properly"
    # implement load_module(), instead loading the code from the zip
    # file when the object is instantiated. This means that calling
    # reload() by itself does nothing. Instead we have to refresh the
    # actual source code and then call reload().
    pc_package_path = os.path.dirname(__file__)
    if pc_package_path.endswith('.sublime-package'):
        refreshing_zip_loader = sublime_plugin.ZipLoader(pc_package_path)
        pc_zip_loader = sys.modules[commands_name].__loader__
        if hasattr(pc_zip_loader, 'contents') and hasattr(pc_zip_loader, 'packages'):
            pc_zip_loader.contents = refreshing_zip_loader.contents
            pc_zip_loader.packages = refreshing_zip_loader.packages

        if pc_package_path in zipimport._zip_directory_cache:
            del zipimport._zip_directory_cache[pc_package_path]
        is_zipped = True

    importlib.invalidate_caches()
    do_insert = True


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
    '.text',
    '.cache',
    '.file_not_found_error',
    '.open_compat',
    '.http_cache',
    '.console_write',
    '.unicode',
    '.clear_directory',
    '.show_error',
    '.cmd',
    '.processes',
    '.settings',
    '.show_quick_panel',
    '.thread_progress',
    '.package_io',
    '.semver',
    '.versions',

    '.http',
    '.http.x509',
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
    '.downloaders.caching_downloader',
    '.downloaders.decoding_downloader',
    '.downloaders.limiting_downloader',
    '.downloaders.urllib_downloader',
    '.downloaders.cli_downloader',
    '.downloaders.curl_downloader',
    '.downloaders.wget_downloader',
    '.downloaders.wininet_downloader',
    '.downloaders.background_downloader',
    '.downloaders',

    '.download_manager',

    '.clients',
    '.clients.client_exception',
    '.clients.bitbucket_client',
    '.clients.github_client',
    '.clients.readme_client',
    '.clients.json_api_client',

    '.providers.provider_exception',
    '.providers.bitbucket_repository_provider',
    '.providers.github_repository_provider',
    '.providers.github_user_provider',
    '.providers.schema_compat',
    '.providers.release_selector',
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
    '.package_installer',
    '.package_renamer',

    '.loader',
    '.bootstrap',

    '.tests',
    '.tests.clients',
    '.tests.providers',

    '.commands',
    '.commands.add_channel_command',
    '.commands.add_repository_command',
    '.commands.create_package_command',
    '.commands.disable_package_command',
    '.commands.discover_packages_command',
    '.commands.enable_package_command',
    '.commands.existing_packages_command',
    '.commands.install_local_dependency_command',
    '.commands.install_package_command',
    '.commands.list_packages_command',
    '.commands.list_unmanaged_packages_command',
    '.commands.remove_channel_command',
    '.commands.remove_package_command',
    '.commands.remove_repository_command',
    '.commands.upgrade_all_packages_command',
    '.commands.upgrade_package_command',
    '.commands.package_control_insert_command',
    '.commands.satisfy_dependencies_command',
    '.commands.package_control_tests_command',

    '.automatic_upgrader',
    '.package_cleanup'
]


if do_insert:
    if is_zipped:
        # When we run into modules imports from a .sublime-package, the
        # in memory modules reference a zipimport.zipimporter object that
        # has an out-dated reference to the .sublime-package file, which
        # means when we call reload(), we get a zipimport.ZipImportError
        # of "bad local file header". To work around this, we construct
        # new zipimporter instances and attach them to the in-memory
        # modules using the .__loader__ attribute.
        loaders = {}
        loaders[''] = zipimport.zipimporter(pc_package_path)
    else:
        sys.path.insert(0, pc_package_path)

for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        try:
            reload(sys.modules[mod])
        except (ImportError):
            pass  # Upgrade issues from PC 2.0 -> 3.0
    if sys.version_info >= (3,):
        bare_mod = bare_mod_prefix + suffix
        if bare_mod in reload_mods:
            bare_module = sys.modules[bare_mod]
            if is_zipped:
                # See the command above near "if is_zipped:" to understand why
                # we are replacing the .__loader__ attribute of the modules with
                # a fresh zipimporter object.
                if bare_mod.find('.') == -1:
                    loader_lookup = ''
                else:
                    loader_lookup = os.sep.join(bare_mod.split('.')[0:-1])
                    if loader_lookup not in loaders:
                        loaders[loader_lookup] = zipimport.zipimporter(os.path.join(pc_package_path, loader_lookup) + os.sep)
                bare_module.__loader__ = loaders[loader_lookup]
            reload(bare_module)

if do_insert and not is_zipped:
    sys.path.remove(pc_package_path)
