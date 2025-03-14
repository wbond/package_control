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

    '.download_manager',

    '.clients',
    '.clients.client_exception',
    '.clients.json_api_client',
    '.clients.bitbucket_client',
    '.clients.github_client',
    '.clients.gitlab_client',
    '.clients.readme_client',

    '.providers.schema_version',
    '.providers.provider_exception',
    '.providers.base_repository_provider',
    '.providers.bitbucket_repository_provider',
    '.providers.github_repository_provider',
    '.providers.github_user_provider',
    '.providers.gitlab_repository_provider',
    '.providers.gitlab_user_provider',
    '.providers.json_repository_provider',
    '.providers.channel_provider',
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
    '.tests._config',
    '.tests._data_decorator',
    '.tests.test_clients',
    '.tests.test_distinfo',
    '.tests.test_downloaders',
    '.tests.test_package_versions',
    '.tests.test_pep440_specifier',
    '.tests.test_pep440_version',
    '.tests.test_pep508_marker',
    '.tests.test_providers',
    '.tests.test_selectors',

    '.commands.add_channel_command',
    '.commands.add_repository_command',
    '.commands.clear_package_cache_command',
    '.commands.create_package_command',
    '.commands.disable_package_command',
    '.commands.disable_packages_command',
    '.commands.discover_packages_command',
    '.commands.enable_package_command',
    '.commands.enable_packages_command',
    '.commands.existing_packages_command',
    '.commands.install_package_command',
    '.commands.install_packages_command',
    '.commands.list_available_libraries_command',
    '.commands.list_packages_command',
    '.commands.list_unmanaged_packages_command',
    '.commands.new_template_command',
    '.commands.remove_channel_command',
    '.commands.remove_package_command',
    '.commands.remove_packages_command',
    '.commands.remove_repository_command',
    '.commands.revert_package_command',
    '.commands.upgrade_all_packages_command',
    '.commands.upgrade_package_command',
    '.commands.satisfy_libraries_command',
    '.commands.satisfy_packages_command',
    '.commands.package_control_edit_settings_command',
    '.commands.package_control_disable_debug_mode_command',
    '.commands.package_control_enable_debug_mode_command',
    '.commands.package_control_insert_command',
    '.commands.package_control_message_command',
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
