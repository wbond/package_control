import os
import sublime
import sys

# Clear module cache to force reloading all modules of this package.
prefix1 = __package__ + "."     # sub modules of Package Control package
prefix2 = "package_control."    # sub modules of package_control namespace package
for module_name in [
    module_name
    for module_name in sys.modules
    if (module_name.startswith(prefix1) or module_name.startswith(prefix2)) and module_name != __name__
]:
    del sys.modules[module_name]
del prefix1
del prefix2

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
