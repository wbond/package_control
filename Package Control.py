import sublime
import sys
import os


st_version = 2

# Warn about out-dated versions of ST3
if sublime.version() == '':
    st_version = 3
    print('Package Control: Please upgrade to Sublime Text 3 build 3012 or newer')

elif int(sublime.version()) > 3000:
    st_version = 3


if st_version == 3:
    installed_dir, _ = __name__.split('.')
elif st_version == 2:
    installed_dir = os.path.basename(os.getcwd())


# Ensure the user has installed Package Control properly
if installed_dir != 'Package Control':
    message = (u"Package Control\n\nThis package appears to be installed " +
        u"incorrectly.\n\nIt should be installed as \"Package Control\", " +
        u"but seems to be installed as \"%s\".\n\n" % installed_dir)
    # If installed unpacked
    if os.path.exists(os.path.join(sublime.packages_path(), installed_dir)):
        message += (u"Please use the Preferences > Browse Packages... menu " +
            u"entry to open the \"Packages/\" folder and rename" +
            u"\"%s/\" to \"Package Control/\" " % installed_dir)
    # If installed as a .sublime-package file
    else:
        message += (u"Please use the Preferences > Browse Packages... menu " +
            u"entry to open the \"Packages/\" folder, then browse up a " +
            u"folder and into the \"Installed Packages/\" folder.\n\n" +
            u"Inside of \"Installed Packages/\", rename " +
            u"\"%s.sublime-package\" to " % installed_dir +
            u"\"Package Control.sublime-package\" ")
    message += u"and restart Sublime Text."
    sublime.error_message(message)

# Normal execution will finish setting up the package
else:
    reloader_name = 'package_control.reloader'

    # ST3 loads each package as a module, so it needs an extra prefix
    if st_version == 3:
        reloader_name = 'Package Control.' + reloader_name
        from imp import reload

    # Make sure all dependencies are reloaded on upgrade
    if reloader_name in sys.modules:
        reload(sys.modules[reloader_name])


    try:
        # Python 3
        from .package_control import reloader

        from .package_control.commands import *
        from .package_control.package_cleanup import PackageCleanup

    except (ValueError):
        # Python 2
        from package_control import reloader
        from package_control import sys_path

        from package_control.commands import *
        from package_control.package_cleanup import PackageCleanup


    def plugin_loaded():
        # Start shortly after Sublime starts so package renames don't cause errors
        # with keybindings, settings, etc disappearing in the middle of parsing
        sublime.set_timeout(lambda: PackageCleanup().start(), 2000)

    if st_version == 2:
        plugin_loaded()
