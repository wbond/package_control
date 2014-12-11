import sys
import os
from os.path import dirname

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

import sublime



if sys.version_info >= (3,):
    def decode(path):
        return path

    def encode(path):
        return path

    if os.path.basename(__file__) == 'sys_path.py':
        pc_package_path = dirname(dirname(__file__))
    # When loaded as a .sublime-package file, the filename ends up being
    # Package Control.sublime-package/Package Control.package_control.sys_path
    else:
        pc_package_path = dirname(__file__)
    st_version = u'3'

else:
    def decode(path):
        if not isinstance(path, unicode):
            path = path.decode(sys.getfilesystemencoding())
        return path

    def encode(path):
        if isinstance(path, unicode):
            path = path.encode(sys.getfilesystemencoding())
        return path

    pc_package_path = decode(os.getcwd())
    st_version = u'2'


st_dir = dirname(dirname(pc_package_path))


def add(path, first=False):
    """
    Adds an entry to the beginning of sys.path, working around the fact that
    Python 2.6 can't import from non-ASCII paths on Windows.

    :param path:
        A unicode string of a folder, zip file or sublime-package file to
        add to the path

    :param first:
        If the path should be added at the beginning
    """

    if os.name == 'nt':
        # Work around unicode path import issue on Windows with Python 2.6
        buf = create_unicode_buffer(512)
        if windll.kernel32.GetShortPathNameW(path, buf, len(buf)):
            path = buf.value

    enc_path = encode(path)

    if os.path.exists(enc_path):
        if first:
            try:
                sys.path.remove(enc_path)
            except (ValueError):
                pass
            sys.path.insert(0, enc_path)
        elif enc_path not in sys.path:
            sys.path.append(enc_path)


def remove(path):
    """
    Removes a path from sys.path if it is present

    :param path:
        A unicode string of a folder, zip file or sublime-package file
    """

    try:
        sys.path.remove(encode(path))
    except (ValueError):
        pass

    if os.name == 'nt':
        buf = create_unicode_buffer(512)
        if windll.kernel32.GetShortPathNameW(path, buf, len(buf)):
            path = buf.value
        try:
            sys.path.remove(encode(path))
        except (ValueError):
            pass


def generate_dependency_paths(name):
    """
    Accepts a dependency name and generates a dict containing the three standard
    import paths that are valid for the current machine.

    :param name:
        A unicode string name of the dependency

    :return:
        A dict with the following keys:
         - 'ver'
         - 'plat'
         - 'arch'
    """

    packages_dir = os.path.join(st_dir, u'Packages')
    dependency_dir = os.path.join(packages_dir, name)

    ver = u'st%s' % st_version
    plat = sublime.platform()
    arch = sublime.arch()

    return {
        'ver': os.path.join(dependency_dir, ver),
        'plat': os.path.join(dependency_dir, u'%s_%s' % (ver, plat)),
        'arch': os.path.join(dependency_dir, u'%s_%s_%s' % (ver, plat, arch))
    }


def add_dependency(name, first=False):
    """
    Accepts a dependency name and automatically adds the appropriate path
    to sys.path, if the dependency has a path for the current platform and
    architecture.

    :param name:
        A unicode string name of the dependency

    :param first:
        If the path should be added to the beginning of the list
    """

    dep_paths = generate_dependency_paths(name)

    for type_ in dep_paths:
        if os.path.exists(encode(dep_paths[type_])):
            add(dep_paths[type_], first=first)
