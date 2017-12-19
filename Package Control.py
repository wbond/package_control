import os
import sublime

try:
    if int(sublime.version()) < 3000:
        from package_control import text
        message = text.format(
            '''
            Package Control

            Sublime Text 3 is required.

            To fix the issue, please install the latest stable Sublime Text version.
            '''
        )
        raise ImportError(message)

    from .package_control import sys_path
    from .package_control import text

    # Ensure the user has installed Package Control properly
    if __package__ != 'Package Control':
        message = text.format(
            '''
            Package Control

            This package appears to be installed incorrectly.

            It should be installed as "Package Control",
            but seems to be installed as "%s".

            To fix the issue, please:

            1. Open the "Preferences" menu
            2. Select "Browse Packages\u2026"
            ''',
            __package__,
            strip=False
        )
        # If installed unpacked
        if os.path.exists(os.path.join(sys_path.packages_path, __package__)):
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
        raise ImportError(message)

    has_packed = os.path.exists(os.path.join(
        sys_path.installed_packages_path, 'Package Control.sublime-package'))
    has_unpacked = os.path.exists(os.path.join(
        sys_path.packages_path, 'Package Control', 'Package Control.py'))
    if has_packed and has_unpacked:
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
        raise ImportError(message)

    # Normal execution will finish setting up the package
    from .package_control.commands import *  # noqa
    from .package_control.console_write import console_write
    from .package_control.package_cleanup import PackageCleanup
    from .package_control.settings import pc_settings_filename

    def plugin_loaded():
        # Make sure the user's locale can handle non-ASCII. A whole bunch of
        # work was done to try and make Package Control work even if the locale
        # was poorly set, by manually encoding all file paths, but it ended up
        # being a fool's errand since the package loading code built into
        # Sublime Text is not written to work that way, and although packages
        # could be installed, they could not be loaded properly.
        try:
            os.path.exists(os.path.join(sublime.packages_path(), "fran\u00e7ais"))
        except UnicodeEncodeError:
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
                '''
            )
            sublime.error_message(message)
            return

        pc_settings = sublime.load_settings(pc_settings_filename())
        if not pc_settings.get('bootstrapped'):
            console_write('Not running package cleanup since bootstrapping is not yet complete.')
            return

        # Start shortly after Sublime starts so package renames don't cause errors
        # with keybindings, settings, etc disappearing in the middle of parsing
        sublime.set_timeout(lambda: PackageCleanup().start(), 2000)

# Display the import errors generated during the import run of this module.
# The error box is delayed because ST2 wouldn't start otherwise.
except ImportError as error:
    sublime.set_timeout(lambda: sublime.error_message(str(error)), 2000)
