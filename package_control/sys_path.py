import os
import sys

from zipimport import zipimporter

import sublime

data_dir = None
packages_path = None
installed_packages_path = None

# Unpacked install of Sublime Text
if not isinstance(__loader__, zipimporter):
    pc_package_path = os.path.dirname(os.path.dirname(__file__))
    packages_path = os.path.dirname(pc_package_path)
    # For a non-development build, the Installed Packages are next
    # to the Packages dir
    _possible_installed_packages_path = os.path.join(os.path.dirname(packages_path), 'Installed Packages')
    if os.path.exists(_possible_installed_packages_path):
        installed_packages_path = _possible_installed_packages_path

# When loaded as a .sublime-package file, the filename ends up being
# Package Control.sublime-package/Package Control.package_control.sys_path
else:
    pc_package_path = os.path.dirname(os.path.dirname(__file__))
    installed_packages_path = os.path.dirname(pc_package_path)
    # For a non-development build, the Packages are next
    # to the Installed Packages dir
    _possible_packages_path = os.path.join(os.path.dirname(installed_packages_path), 'Packages')
    if os.path.exists(_possible_packages_path):
        packages_path = _possible_packages_path

if packages_path is None:
    import Default.sort

    if not isinstance(Default.sort.__loader__, zipimporter):
        packages_path = os.path.dirname(os.path.dirname(Default.sort.__file__))

if installed_packages_path is None:
    _data_base = None
    if sys.platform == 'darwin':
        _data_base = os.path.expanduser('~/Library/Application Support')
    elif sys.platform == 'win32':
        _data_base = os.environ.get('APPDATA')
    else:
        _data_base = os.environ.get('XDG_CONFIG_HOME')
        if _data_base is None:
            _data_base = os.path.expanduser('~/.config')

    if _data_base is not None:
        for _leaf in ['Sublime Text Development', 'Sublime Text 3 Development']:
            if sys.platform not in set(['win32', 'darwin']):
                _leaf = _leaf.lower().replace(' ', '-')
            _possible_data_dir = os.path.join(_data_base, _leaf)
            if os.path.exists(_possible_data_dir):
                data_dir = _possible_data_dir
                _possible_installed_packages_path = os.path.join(data_dir, u'Installed Packages')
                if os.path.exists(_possible_installed_packages_path):
                    installed_packages_path = _possible_installed_packages_path
                break

if installed_packages_path and data_dir is None:
    data_dir = os.path.dirname(installed_packages_path)


def decode(path):
    return path


def encode(path):
    return path


def add(path, first=False):
    """
    Add a path from sys.path if it is present.

    :param path:
        A string of a folder, zip file or sublime-package file

    :param first:
        If the path should be added at the beginning
    """

    if path not in sys.path:
        if first:
            sys.path.insert(0, path)
        else:
            sys.path.append(path)


def remove(path):
    """
    Remove a path from sys.path if it is present.

    :param path:
        A string of a folder, zip file or sublime-package file
    """

    try:
        sys.path.remove(path)
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

    ver = 'st3'
    plat = sublime.platform()
    arch = sublime.arch()

    return {
        'all': os.path.join(dependency_dir, 'all'),
        'ver': os.path.join(dependency_dir, ver),
        'plat': os.path.join(dependency_dir, '%s_%s' % (ver, plat)),
        'arch': os.path.join(dependency_dir, '%s_%s_%s' % (ver, plat, arch))
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

    for path in generate_dependency_paths(name).values():
        if os.path.exists(path):
            add(path, first=first)
