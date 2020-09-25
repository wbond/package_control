import threading
from textwrap import dedent

import sublime

from .package_control.bootstrap import mark_bootstrapped
from .package_control.package_manager import PackageManager
from .package_control import loader


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
        import sys
        import os
        from os.path import dirname


        # This file adds the package_control subdirectory of Package Control
        # to first in the sys.path so that all other packages may rely on
        # PC for utility functions, such as event helpers, adding things to
        # sys.path, downloading files from the internet, etc


        def decode(path):
            return path

        def encode(path):
            return path

        loader_dir = dirname(__file__)


        st_dir = dirname(dirname(loader_dir))

        found = False
        installed_packages_dir = os.path.join(st_dir, 'Installed Packages')
        pc_package_path = os.path.join(installed_packages_dir, 'Package Control.sublime-package')
        if os.path.exists(encode(pc_package_path)):
            found = True

        if not found:
            packages_dir = os.path.join(st_dir, 'Packages')
            pc_package_path = os.path.join(packages_dir, 'Package Control')
            if os.path.exists(encode(pc_package_path)):
                found = True

        # Handle the development environment
        if not found:
            import Default.sort
            if os.path.basename(Default.sort.__file__) == 'sort.py':
                packages_dir = dirname(dirname(Default.sort.__file__))
                pc_package_path = os.path.join(packages_dir, 'Package Control')
                if os.path.exists(encode(pc_package_path)):
                    found = True

        if found:
            if os.name == 'nt':
                from ctypes import windll, create_unicode_buffer
                buf = create_unicode_buffer(512)
                if windll.kernel32.GetShortPathNameW(pc_package_path, buf, len(buf)):
                    pc_package_path = buf.value

            sys.path.insert(0, encode(pc_package_path))
            import package_control
            # We remove the import path right away so as not to screw up
            # Sublime Text and its import machinery
            sys.path.remove(encode(pc_package_path))

        else:
            print('Package Control: Error finding main directory from loader')
    """
    base_loader_code = dedent(base_loader_code).lstrip()
    loader.add_or_update('00', 'package_control', base_loader_code)

    sublime.set_timeout(mark_bootstrapped, 10)
