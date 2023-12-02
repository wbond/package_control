import atexit
import os
import shutil
import sys
import tempfile

_ST_DIR = None


def _st_dir():
    global _ST_DIR

    if _ST_DIR is None:
        _ST_DIR = os.environ.get("ST_DIR")
        if _ST_DIR:
            _ST_DIR = os.path.abspath(os.path.expanduser(os.path.expandvars(_ST_DIR)))
        else:
            _ST_DIR = tempfile.mkdtemp(prefix="package_control-tests")

        os.makedirs(_ST_DIR, exist_ok=True)
        os.mkdir(os.path.join(_ST_DIR, 'Data'))
        os.mkdir(os.path.join(_ST_DIR, 'Data', 'Cache'))
        os.mkdir(os.path.join(_ST_DIR, 'Data', 'Installed Packages'))
        os.mkdir(os.path.join(_ST_DIR, 'Data', 'Packages'))
        os.mkdir(os.path.join(_ST_DIR, 'Data', 'Packages', 'User'))
        os.mkdir(os.path.join(_ST_DIR, 'Packages'))

    return _ST_DIR


def cache_path():
    return os.path.join(_st_dir(), 'Data', 'Cache')


def installed_packages_path():
    return os.path.join(_st_dir(), 'Data', 'Installed Packages')


def packages_path():
    return os.path.join(_st_dir(), 'Data', 'Packages')


def executable_path():
    if sys.platform == 'win32':
        return os.path.join(_st_dir(), 'sublime_text.exe')
    return os.path.join(_st_dir(), 'sublime_text')


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
    if _ST_DIR:
        shutil.rmtree(_ST_DIR)


atexit.register(_cleanup_temp_dir)
