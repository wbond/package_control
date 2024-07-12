import os
import sys

import sublime

PREFIX = '\\\\?\\' if sys.platform == 'win32' else ''

__executable_path = sublime.executable_path()
if not __executable_path:
    # Until ST4187 sublime.executable_path() doesn't return anything at import time.
    # On python 3.3 os.abspath() is required to return absolute path of sys.executable
    __executable_path = os.path.abspath(sys.executable)

# Default packages are located in application installation directory next to executables.
__default_packages_path = os.path.join(os.path.dirname(__executable_path), 'Packages')
if not os.path.isdir(__default_packages_path):
    # Fall back to detecting the path using the location of the module
    import Default.sort as default_module
    __default_packages_path = os.path.dirname(os.path.dirname(default_module.__file__))

if not os.path.isdir(__default_packages_path):
    raise FileNotFoundError('Default Packages')

# Determine user's data path.
# - for portable setups resolves to __executable_path/Data
# - for Normal setups resolves to %APPDATA%\Sublime Text or ~/.config/sublime-text
# When loaded as a .sublime-package file, __file__ ends up being
# {data_dir}/Installed Packages/Package Control.sublime-package/package_control/sys_path.py
# When loaded as unpacked package, __file__ ends up being
# {data_dir}/Packages/Package Control/package_control/sys_path.py
__data_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Determine extracted packages path
__packages_path = os.path.join(__data_path, 'Packages')
if not os.path.isdir(__packages_path):
    # in ST development environment default package must be a directory
    if not os.path.isdir(os.path.join(__default_packages_path, 'Default')):
        raise FileNotFoundError('Packages')
    __packages_path = __default_packages_path

# Determine installed packages path
__installed_packages_path = os.path.join(__data_path, 'Installed Packages')
if not os.path.isdir(__installed_packages_path):
    __installed_packages_path = None

if __installed_packages_path is None:
    if sys.platform == 'darwin':
        __data_path = os.path.expanduser('~/Library/Application Support')
    elif sys.platform == 'win32':
        __data_path = os.environ.get('APPDATA')
    else:
        __data_path = os.environ.get('XDG_CONFIG_HOME')
        if __data_path is None:
            __data_path = os.path.expanduser('~/.config')

    if __data_path:
        for __leaf in ('Sublime Text Development', 'Sublime Text 3 Development'):
            if sys.platform not in set(('win32', 'darwin')):
                __leaf = __leaf.lower().replace(' ', '-')
            __data_path = os.path.join(__data_path, __leaf)
            __installed_packages_path = os.path.join(__data_path, 'Installed Packages')
            if not os.path.exists(__installed_packages_path):
                __installed_packages_path = None

    if __installed_packages_path is None:
        raise FileNotFoundError('Installed Packages')

if PREFIX:
    __data_path = PREFIX + __data_path
    __default_packages_path = PREFIX + __default_packages_path
    __installed_packages_path = PREFIX + __installed_packages_path
    __packages_path = PREFIX + __packages_path

__cache_path = None
__package_control_cache_path = None
__python_libs_cache_path = None
__python_packages_cache_path = None
__trash_path = os.path.join(__data_path, "Trash")
__user_config_path = os.path.join(__packages_path, 'User')


def add_dependency(name, first=False):
    """
    A backward compatibility dummy

    1. Satisfies 01_package_control_loader until migration is complete.
       Reduces amount of tracebacks printed to console.

    2. Some plugins such as AutomaticPackageReloader make use of it, too.
    """
    pass


def cache_path():
    """
    Returns the ST cache directory

    :return:
        A string of ST's cache directory
    """
    global __cache_path

    if not __cache_path:
        cache_path = sublime.cache_path()
        if not cache_path:
            raise RuntimeError("ST API error: cache_path() returned None!")
        __cache_path = PREFIX + sublime.cache_path()

    return str(__cache_path)


def data_path():
    """
    Returns the ST data directory

    :return:
        A string of ST's data directory
    """

    return str(__data_path)


def lib_paths():
    """
    Returns a dict of version-specific lib folders

    :return:
        A dict with the key "3.3" and possibly the key "3.8"
    """
    try:
        return lib_paths.cache
    except AttributeError:
        lib_paths.cache = {
            "3.3": os.path.join(__data_path, "Lib", "python33"),
            "3.8": os.path.join(__data_path, "Lib", "python38")
        } if int(sublime.version()) >= 4000 else {
            "3.3": os.path.join(__data_path, "Lib", "python3.3")
        }
        return lib_paths.cache


def default_packages_path():
    """
    Returns the ST default/bundled packages directory

    :return:
        A string of ST's default packages directory
    """

    return str(__default_packages_path)


def installed_packages_path():
    """
    Returns the ST installed packages directory

    :return:
        A string of ST's installed packages directory
    """

    return str(__installed_packages_path)


def packages_path():
    """
    Returns the ST packages directory

    :return:
        A string of ST's packages directory
    """

    return str(__packages_path)


def trash_path():
    """
    Returns the ST trash directory

    :return:
        A string of ST's trash directory
    """

    return str(__trash_path)


def python_libs_cache_path(python_version):
    """
    Returns the libraries' module cache directory

    :return:
        A string of ST's python cache directory of installed libraries
    """

    global __python_libs_cache_path

    if not __python_libs_cache_path:
        __python_libs_cache_path = {
            "3.3": None,    # bytecode cache not supported
            "3.8": os.path.join(
                cache_path(), '__pycache__', 'install', 'Data', 'Lib', "python38")
        }

    return str(__python_libs_cache_path[python_version])


def python_packages_cache_path():
    """
    Returns the packages' module cache directory

    :return:
        A string of ST's python cache directory of installed packages
    """

    global __python_packages_cache_path

    if not __python_packages_cache_path:
        __python_packages_cache_path = os.path.join(
            cache_path(), '__pycache__', 'install', 'Data', 'Packages')

    return str(__python_packages_cache_path)


def pc_cache_dir():
    """
    Returns the cache directory for Package Control files

    :return:
        A string of the Package Control cache directory
    """

    global __package_control_cache_path

    if not __package_control_cache_path:
        __package_control_cache_path = os.path.join(cache_path(), 'Package Control')

    return str(__package_control_cache_path)


def user_config_dir():
    """
    Returns the directory for the user's config

    :return:
        A string of the User configuration directory
    """

    return str(__user_config_path)


def longpath(path):
    """
    Normalize path, eliminating double slashes, etc.

    This is a patched version of ntpath.normpath(), which

    1. replaces `/` by `\\` on Windows, even if the absolute path specified is
       already prefixed by \\\\?\\ or \\\\.\\ to make sure to avoid WinError 123
       when calling functions like ntpath.realpath().

    2. always prepends \\\\?\\ on Windows to enable long paths support.

    This is to workaround some shortcomings of python stdlib.

    :param path:
        The absolute path to normalize

    :returns:
        A normalized path string
    """

    if PREFIX:
        special_prefixes = (PREFIX, '\\\\.\\')
        if path.startswith(special_prefixes):
            return os.path.normpath(path.replace('/', '\\'))
        return PREFIX + os.path.normpath(path)
    return os.path.normpath(path)


def shortpath(path):
    """
    Return unprefixed absolute path

    :param path:
        The absolute path to remove prefix from

    :returns:
        An unprefixed path string
    """
    return path[len(PREFIX):] if path.startswith(PREFIX) else path
