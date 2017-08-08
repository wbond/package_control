import sys
import os
from os.path import dirname

import sublime

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

try:
    str_cls = unicode
except (NameError):
    str_cls = str
    from zipimport import zipimporter

data_dir = None
packages_path = None
installed_packages_path = None

if sys.version_info >= (3,):
    def decode(path):
        return path

    def encode(path):
        return path

    # Unpacked install of Sublime Text
    if not isinstance(__loader__, zipimporter):
        pc_package_path = dirname(dirname(__file__))
        packages_path = dirname(pc_package_path)
        # For a non-development build, the Installed Packages are next
        # to the Packages dir
        _possible_installed_packages_path = os.path.join(dirname(packages_path), u'Installed Packages')
        if os.path.exists(_possible_installed_packages_path):
            installed_packages_path = _possible_installed_packages_path

    # When loaded as a .sublime-package file, the filename ends up being
    # Package Control.sublime-package/Package Control.package_control.sys_path
    else:
        pc_package_path = dirname(dirname(__file__))
        installed_packages_path = dirname(pc_package_path)
        # For a non-development build, the Packages are next
        # to the Installed Packages dir
        _possible_packages_path = os.path.join(dirname(installed_packages_path), u'Packages')
        if os.path.exists(_possible_packages_path):
            packages_path = _possible_packages_path
    st_version = u'3'

    if packages_path is None:
        import Default.sort

        if not isinstance(Default.sort.__loader__, zipimporter):
            packages_path = dirname(dirname(Default.sort.__file__))

    if installed_packages_path is None:
        _data_base = None
        if sys.platform == 'darwin':
            _data_base = os.path.expanduser(u'~/Library/Application Support')
        elif sys.platform == 'win32':
            _data_base = os.environ.get(u'APPDATA')
        else:
            _data_base = os.environ.get(u'XDG_CONFIG_HOME')
            if _data_base is None:
                _data_base = os.path.expanduser('~/.config')

        if _data_base is not None:
            _config_leaf = u'Sublime Text 3 Development'
            if sys.platform not in set(['win32', 'darwin']):
                _config_leaf = u'sublime-text-3-development'
            _possible_data_dir = os.path.join(_data_base, _config_leaf)
            if os.path.exists(_possible_data_dir):
                data_dir = _possible_data_dir
                _possible_installed_packages_path = os.path.join(data_dir, u'Installed Packages')
                if os.path.exists(_possible_installed_packages_path):
                    installed_packages_path = _possible_installed_packages_path

    if installed_packages_path and data_dir is None:
        data_dir = dirname(installed_packages_path)

else:
    def decode(path):
        if not isinstance(path, str_cls):
            path = path.decode(sys.getfilesystemencoding())
        return path

    def encode(path):
        if isinstance(path, str_cls):
            path = path.encode(sys.getfilesystemencoding())
        return path

    pc_package_path = decode(os.getcwd())
    packages_path = dirname(pc_package_path)
    data_dir = dirname(packages_path)
    installed_packages_path = os.path.join(data_dir, u'Installed Packages')
    st_version = u'2'


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

    dependency_dir = os.path.join(packages_path, name)

    ver = u'st%s' % st_version
    plat = sublime.platform()
    arch = sublime.arch()

    return {
        'all': os.path.join(dependency_dir, u'all'),
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

    for path in dep_paths.values():
        if os.path.exists(encode(path)):
            add(path, first=first)
