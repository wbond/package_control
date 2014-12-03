import sys
import threading
from textwrap import dedent

import sublime

if sys.version_info < (3,):
    from package_control.bootstrap import bootstrap_dependency
    from package_control.package_manager import PackageManager
    from package_control import loader
else:
    from .package_control.bootstrap import bootstrap_dependency
    from .package_control.package_manager import PackageManager
    from .package_control import loader


def plugin_loaded():
    manager = PackageManager()
    settings = manager.settings.copy()

    if not settings.get('installed_dependencies', []):
        base_loader_code = """
            import sys
            import os
            from os.path import dirname


            # This file adds the package_control subdirectory of Package Control
            # to first in the sys.path so that all other packages may rely on
            # PC for utility functions, such as event helpers, adding things to
            # sys.path, downloading files from the internet, etc


            if sys.version_info >= (3,):
                def decode(path):
                    return path

                def encode(path):
                    return path

                loader_dir = dirname(__file__)

            else:
                def decode(path):
                    if not isinstance(path, unicode):
                        path = path.decode(sys.getfilesystemencoding())
                    return path

                def encode(path):
                    if isinstance(path, unicode):
                        path = path.encode(sys.getfilesystemencoding())
                    return path

                loader_dir = decode(os.getcwd())


            st_dir = dirname(dirname(loader_dir))

            found = False
            if sys.version_info >= (3,):
                installed_packages_dir = os.path.join(st_dir, u'Installed Packages')
                pc_package_path = os.path.join(installed_packages_dir, u'Package Control.sublime-package')
                if os.path.exists(encode(pc_package_path)):
                    found = True

            if not found:
                packages_dir = os.path.join(st_dir, u'Packages')
                pc_package_path = os.path.join(packages_dir, u'Package Control')
                if os.path.exists(encode(pc_package_path)):
                    found = True

            if found:
                if os.name == 'nt':
                    from ctypes import windll, create_unicode_buffer
                    buf = create_unicode_buffer(512)
                    if windll.kernel32.GetShortPathNameW(pc_package_path, buf, len(buf)):
                        pc_package_path = buf.value

                sys.path.insert(0, encode(pc_package_path))

            else:
                print(u'Package Control: Error finding main directory from loader')
        """
        base_loader_code = dedent(base_loader_code)
        loader.add('000', 'package_control', base_loader_code)

    # SSL support fo Linux
    if sublime.platform() == 'linux':
        linux_ssl_url = u'http://packagecontrol.io/ssl-linux.sublime-package'
        linux_ssl_hash = u'd12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4'
        linux_ssl_priority = u'001'

        def linux_ssl_show_restart():
            sublime.message_dialog(u'Package Control\n\n'
                u'Package Control just installed the missing Python _ssl ' + \
                u'module for Linux since Sublime Text does not include it.\n\n' + \
                u'Please restart Sublime Text to make SSL available to all ' + \
                u'packages.')

        linux_ssl_args = (settings, linux_ssl_url,
            linux_ssl_hash, linux_ssl_priority, linux_ssl_show_restart)
        threading.Thread(target=bootstrap_dependency, args=linux_ssl_args).start()


    # SSL support for SHA-2 certificates with ST2 on Windows
    if sublime.platform() == 'windows' and sys.version_info < (3,):
        win_ssl_url = u'http://packagecontrol.io/ssl-windows.sublime-package'
        win_ssl_hash = u'efe25e3bdf2e8f791d86327978aabe093c9597a6ceb8c2fb5438c1d810e02bea'
        win_ssl_priority = u'001'

        def win_ssl_show_restart():
            sublime.message_dialog(u'Package Control\n\n'
                u'Package Control just upgraded the Python _ssl module for ' + \
                u'ST2 on Windows because the bundled one does not include ' + \
                u'support for modern SSL certificates.\n\n' + \
                u'Please restart Sublime Text to complete the upgrade.')

        win_ssl_args = (settings, win_ssl_url, win_ssl_hash,
            win_ssl_priority, win_ssl_show_restart)
        threading.Thread(target=bootstrap_dependency, args=win_ssl_args).start()

# ST2 compat
if sys.version_info < (3,):
    plugin_loaded()
