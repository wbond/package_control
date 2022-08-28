import atexit
import os
import shutil
import tempfile


_TEMP_DIR = None


def _verify_temp_dir():
    global _TEMP_DIR

    if _TEMP_DIR is None:
        _TEMP_DIR = tempfile.mkdtemp('')
        os.mkdir(os.path.join(_TEMP_DIR, 'Cache'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Packages'))
        os.mkdir(os.path.join(_TEMP_DIR, 'Packages', 'User'))


def cache_path():
    _verify_temp_dir()
    return os.path.join(_TEMP_DIR, 'Cache')


def packages_path():
    _verify_temp_dir()
    return os.path.join(_TEMP_DIR, 'Packages')


def arch():
    return "x64"


def platform():
    return "linux"


def version():
    return '4126'


def _cleanup_temp_dir():
    if _TEMP_DIR:
        shutil.rmtree(_TEMP_DIR)


atexit.register(_cleanup_temp_dir)
