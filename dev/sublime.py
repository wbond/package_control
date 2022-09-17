import atexit
import os
import shutil
import sys
import tempfile


_TEMP_DIR = None


def _temp_dir():
    global _TEMP_DIR

    if _TEMP_DIR is None:
        _TEMP_DIR = tempfile.mkdtemp('')
        os.mkdir(os.path.join(_TEMP_DIR, 'Data'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Data', 'Cache'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Data', 'Installed Packages'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Data', 'Packages'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Data', 'Packages', 'User'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Packages'))

    return _TEMP_DIR


def cache_path():
    return os.path.join(_temp_dir(), 'Data', 'Cache')


def installed_packages_path():
    return os.path.join(_temp_dir(), 'Data', 'Installed Packages')


def packages_path():
    return os.path.join(_temp_dir(), 'Data', 'Packages')


def executable_path():
    if sys.platform == 'win32':
        return os.path.join(_temp_dir(), 'sublime_text.exe')
    return os.path.join(_temp_dir(), 'sublime_text')


def arch():
    return 'x64'


def platform():
    if sys.platform == 'darwin':
        return 'osx'
    if sys.platform == 'win32':
        return 'windows'
    return 'linux'


def version():
    return '4126'


def _cleanup_temp_dir():
    if _TEMP_DIR:
        shutil.rmtree(_TEMP_DIR)


atexit.register(_cleanup_temp_dir)
