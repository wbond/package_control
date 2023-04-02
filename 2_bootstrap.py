import json
import os
import shutil
import threading
import zipfile
from textwrap import dedent

import sublime

from .package_control import library, sys_path
from .package_control.console_write import console_write
from .package_control.package_disabler import PackageDisabler
from .package_control.settings import pc_settings_filename
from .package_control.show_error import show_message


LOADER_PACKAGE_NAME = '0_package_control_loader'
LOADER_PACKAGE_PATH = os.path.join(
    sys_path.installed_packages_path(),
    '%s.sublime-package' % LOADER_PACKAGE_NAME
)


def plugin_loaded():
    """
    Run bootstrapping once plugin is loaded

    Bootstapping is executed with little delay to work around a ST core bug,
    which causes `sublime.load_resource()` to fail when being called directly
    by `plugin_loaded()` hook.
    """

    sublime.set_timeout(_plugin_loaded, 100)


def _plugin_loaded():
    if int(sublime.version()) < 3143:
        PackageDisabler.disable_packages({PackageDisabler.DISABLE: "Package Control"})
        return

    if os.path.exists(LOADER_PACKAGE_PATH):
        PackageDisabler.disable_packages({PackageDisabler.LOADER: LOADER_PACKAGE_NAME})

        def start_bootstrap():
            threading.Thread(target=_migrate_loaders).start()

        # Give ST a second to disable 0_package_control_loader
        sublime.set_timeout(start_bootstrap, 1000)
    else:
        _install_injectors()


def _mark_bootstrapped():
    """
    Mark Package Control as successfully bootstrapped
    """

    pc_settings = sublime.load_settings(pc_settings_filename())

    if pc_settings.get('bootstrapped') != 4:
        pc_settings.set('bootstrapped', 4)
        sublime.save_settings(pc_settings_filename())


def _migrate_loaders():
    """
    Moves old Package Control 3-style dependencies to the new 4-style
    libraries, which use the Lib folder
    """

    # All old dependencies that are being migrated are treated as for 3.3
    lib_path = sys_path.lib_paths()["3.3"]

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
                        "3.3",
                        name,
                        metadata['version'],
                        metadata['description'],
                        metadata['url']
                    )
                    library.install(did, lib_path)

                    shutil.rmtree(dep_path)

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
        raise

    _install_injectors()


def _install_injectors():
    """
    Makes sure the module injectors are in place
    """

    injector_code = R"""
        import os
        import zipfile

        import sublime_plugin

        __data_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

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

        elif os.path.exists(__pkg_path):
            from importlib.machinery import SourceFileLoader

            __file_path = os.path.join(__pkg_path,  '__init__.py')

            __loader__ = SourceFileLoader('package_control', __file_path)

            try:
                with open(__file_path, 'r', encoding='utf-8') as __f:
                    __code = compile(__f.read(), '__init__.py', 'exec')
            except (OSError):
                pass

            del globals()['SourceFileLoader']

        if __code is None:
            raise ModuleNotFoundError("No module named 'package_control'")

        __file__ = __file_path
        __package__ = 'package_control'
        __path__ = [__pkg_path]

        # initial cleanup
        del globals()['__f']
        del globals()['__file_path']
        del globals()['__zip_path']
        del globals()['__pkg_path']
        del globals()['__data_path']
        del globals()['sublime_plugin']
        del globals()['zipfile']
        del globals()['os']

        __data = {}
        exec(__code, __data)
        globals().update(__data)

        # Python 3.3 doesn't have __spec__
        if hasattr(globals(), '__spec__'):
            __spec__.loader = __loader__
            __spec__.origin = __file__
            __spec__.submodule_search_locations = __path__
            __spec__.cached = None

        # final cleanup
        del globals()['__data']
        del globals()['__code']
        # out-dated internals
        del globals()['__cached__']
    """

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

    sublime.set_timeout(_mark_bootstrapped, 10)
