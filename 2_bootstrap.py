import threading

from textwrap import dedent

import sublime

st_build = int(sublime.version())
if st_build < 3000:
    raise ImportError('Package Control requires Sublime Text 3')

from .package_control import loader
from .package_control import text
from .package_control.bootstrap import bootstrap_dependency
from .package_control.bootstrap import mark_bootstrapped
from .package_control.package_manager import PackageManager


def plugin_loaded():
    manager = PackageManager()
    settings = manager.settings.copy()
    threading.Thread(target=_background_bootstrap, args=(settings,)).start()


def _background_bootstrap(settings):
    """
    Runs the bootstrap process in a thread since it may need to block to update
    the package control loader

    :param settings:
        A dict of settings
    """

    base_loader_code = """
        import os
        import sys
        from os.path import dirname

        # This file adds the package_control subdirectory of Package Control
        # to first in the sys.path so that all other packages may rely on
        # PC for utility functions, such as event helpers, adding things to
        # sys.path, downloading files from the internet, etc

        loader_dir = dirname(__file__)

        st_dir = dirname(dirname(loader_dir))

        found = False
        installed_packages_dir = os.path.join(st_dir, 'Installed Packages')
        pc_package_path = os.path.join(installed_packages_dir, 'Package Control.sublime-package')
        if os.path.exists(pc_package_path):
            found = True

        if not found:
            packages_dir = os.path.join(st_dir, 'Packages')
            pc_package_path = os.path.join(packages_dir, 'Package Control')
            if os.path.exists(pc_package_path):
                found = True

        # Handle the development environment
        if not found:
            import Default.sort
            if os.path.basename(Default.sort.__file__) == 'sort.py':
                packages_dir = dirname(dirname(Default.sort.__file__))
                pc_package_path = os.path.join(packages_dir, 'Package Control')
                if os.path.exists(pc_package_path):
                    found = True

        if found:
            sys.path.insert(0, pc_package_path)
            import package_control
            # We remove the import path right away so as not to screw up
            # Sublime Text and its import machinery
            sys.path.remove(pc_package_path)

        else:
            print('Package Control: Error finding main directory from loader')
    """
    base_loader_code = dedent(base_loader_code).lstrip()
    loader.add_or_update('00', 'package_control', base_loader_code)

    # SSL support fo Linux
    if sublime.platform() == 'linux' and int(sublime.version()) < 3109:
        linux_ssl_url = 'http://packagecontrol.io/ssl/1.0.2/ssl-linux.sublime-package'
        linux_ssl_hash = '23f35f64458a0a14c99b1bb1bbc3cb04794c7361c4940e0a638d40f038acd377'
        linux_ssl_priority = '01'
        linux_ssl_version = '1.0.2'

        def linux_ssl_show_restart():
            sublime.message_dialog(text.format(
                '''
                Package Control

                Package Control just installed or upgraded the missing Python
                _ssl module for Linux since Sublime Text does not include it.

                Please restart Sublime Text to make SSL available to all
                packages.
                '''
            ))

        threading.Thread(
            target=bootstrap_dependency,
            args=(
                settings,
                linux_ssl_url,
                linux_ssl_hash,
                linux_ssl_priority,
                linux_ssl_version,
                linux_ssl_show_restart,
            )
        ).start()

    else:
        mark_bootstrapped()
