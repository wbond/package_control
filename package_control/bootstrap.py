import json
import os
import zipfile
from textwrap import dedent
from threading import Thread

import sublime

from . import library, sys_path
from .clear_directory import delete_directory
from .console_write import console_write
from .package_cleanup import PackageCleanup
from .package_disabler import PackageDisabler
from .package_io import create_empty_file
from .show_error import show_message


LOADER_PACKAGE_NAME = '0_package_control_loader'
LOADER_PACKAGE_PATH = os.path.join(
    sys_path.installed_packages_path(),
    LOADER_PACKAGE_NAME + '.sublime-package'
)


def disable_package_control():
    """
    Disables Package Control

    Disabling is executed with little delay to work around a ST core bug,
    which causes `sublime.load_resource()` to fail when being called directly
    by `plugin_loaded()` hook.
    """

    sublime.set_timeout(
        lambda: PackageDisabler.disable_packages({PackageDisabler.DISABLE: 'Package Control'}),
        10
    )


def bootstrap():
    """
    Bootstrap Package Control

    Bootstrapping is executed with little delay to work around a ST core bug,
    which causes `sublime.load_resource()` to fail when being called directly
    by `plugin_loaded()` hook.
    """

    if not os.path.exists(LOADER_PACKAGE_PATH):
        # Start shortly after Sublime starts so package renames don't cause errors
        # with key bindings, settings, etc. disappearing in the middle of parsing
        sublime.set_timeout(PackageCleanup().start, 2000)
        return

    sublime.set_timeout(_bootstrap, 10)


def _bootstrap():
    PackageDisabler.disable_packages({PackageDisabler.LOADER: LOADER_PACKAGE_NAME})
    # Give ST a second to disable 0_package_control_loader
    sublime.set_timeout(Thread(target=_migrate_dependencies).start, 1000)


def _migrate_dependencies():
    """
    Moves old Package Control 3-style dependencies to the new 4-style
    libraries, which use the Lib folder
    """

    # All old dependencies that are being migrated are treated as for 3.3
    # or the first available one, if "3.3" is disabled or does not exist.

    python_version = sys_path.python_versions()[0]
    lib_path = sys_path.lib_paths()[python_version]

    try:
        with zipfile.ZipFile(LOADER_PACKAGE_PATH, 'r') as z:
            for path in z.namelist():
                if path == 'dependency-metadata.json':
                    continue
                if path == '00-package_control.py':
                    continue

                name = path[3:-3]
                try:
                    dep_path = os.path.join(sys_path.packages_path(), name)
                    json_path = os.path.join(dep_path, 'dependency-metadata.json')

                    try:
                        with open(json_path, 'r', encoding='utf-8') as fobj:
                            metadata = json.load(fobj)
                    except (OSError, ValueError) as e:
                        console_write('Error loading dependency metadata during migration - %s' % e)
                        continue

                    did = library.convert_dependency(
                        dep_path,
                        python_version,
                        name,
                        metadata['version'],
                        metadata['description'],
                        metadata['url']
                    )
                    library.install(did, lib_path)

                    if not delete_directory(dep_path):
                        create_empty_file(os.path.join(dep_path, 'package-control.cleanup'))

                except (Exception) as e:
                    console_write('Error trying to migrate dependency %s - %s' % (name, e))

        os.remove(LOADER_PACKAGE_PATH)

        def _reenable_loader():
            PackageDisabler.reenable_packages({PackageDisabler.LOADER: LOADER_PACKAGE_NAME})
            show_message(
                '''
                Dependencies have just been migrated to python libraries.

                You may need to restart Sublime Text.
                '''
            )

        sublime.set_timeout(_reenable_loader, 500)

    except (OSError) as e:
        console_write('Error trying to migrate dependencies - %s' % e)


def _install_injectors():
    """
    Makes sure the module injectors are in place
    """

    injector_code = R'''
        """
        Public Package Control API
        """
        import os
        import sys
        import zipfile

        import sublime_plugin

        # python 3.13 may no longer provide __file__
        __data_path = os.path.dirname(os.path.dirname(os.path.dirname(
            __spec__.origin if hasattr(globals(), '__spec__') else __file__))
        )
        __pkg_path = os.path.join(__data_path, 'Packages', 'Package Control', 'package_control')
        __zip_path = os.path.join(__data_path, 'Installed Packages', 'Package Control.sublime-package')
        __code = None

        # We check the .sublime-package first, since the sublime_plugin.ZipLoader deals with overrides
        if os.path.exists(__zip_path):
            __pkg_path = os.path.join(__zip_path, 'package_control')
            __file_path = os.path.join(__pkg_path, '__init__.py')
            __loader__ = sublime_plugin.ZipLoader(__zip_path)

            try:
                with zipfile.ZipFile(__zip_path, 'r') as __f:
                    __code = compile(
                        __f.read('package_control/__init__.py').decode('utf-8'),
                        '__init__.py',
                        'exec'
                    )
            except (OSError, KeyError):
                pass

            # required for events to be available on plugin_host Package Control is not running on
            events = sys.modules.get('package_control.events')
            if events is None:
                events = __loader__.load_module("Package Control.package_control.events")
                events.__name__ = 'package_control.events'
                events.__package__ = 'package_control'
                sys.modules['package_control.events'] = events

        elif os.path.exists(__pkg_path):
            from importlib.machinery import SourceFileLoader

            __file_path = os.path.join(__pkg_path, '__init__.py')
            __loader__ = SourceFileLoader('package_control', __file_path)

            try:
                with open(__file_path, 'r', encoding='utf-8') as __f:
                    __code = compile(__f.read(), '__init__.py', 'exec')
            except (OSError):
                pass

            # required for events to be available on plugin_host Package Control is not running on
            events = sys.modules.get('package_control.events')
            if events is None:
                events = SourceFileLoader('events', os.path.join(__pkg_path, 'events.py')).load_module()
                events.__name__ = 'package_control.events'
                events.__package__ = 'package_control'
                sys.modules['package_control.events'] = events

            del globals()['SourceFileLoader']

        if __code is None:
            raise ModuleNotFoundError("No module named 'package_control'")

        __file__ = __file_path
        __package__ = 'package_control'
        __path__ = [__pkg_path]
        __data = {}
        exec(__code, __data)
        globals().update(__data)

        # cleanup temporary globals
        del globals()['__cached__']
        del globals()['__code']
        del globals()['__data']
        del globals()['__data_path']
        del globals()['__f']
        del globals()['__file_path']
        del globals()['__pkg_path']
        del globals()['__zip_path']
        del globals()['os']
        del globals()['sublime_plugin']
        del globals()['sys']
        del globals()['zipfile']
    '''

    injector_code = dedent(injector_code).lstrip()
    injector_code = injector_code.encode('utf-8')

    for lib_path in sys_path.lib_paths().values():
        injector_path = os.path.join(lib_path, 'package_control.py')

        try:
            with open(injector_path, 'rb') as fobj:
                if injector_code == fobj.read():
                    continue
        except FileNotFoundError:
            pass

        try:
            with open(injector_path, 'wb') as fobj:
                fobj.write(injector_code)
        except FileExistsError:
            pass
        except OSError as e:
            console_write('Unable to write injector to "%s" - %s' % (injector_path, e))


_install_injectors()
