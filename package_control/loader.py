import sys
import os
import re
from os import path
import zipfile
from textwrap import dedent

try:
    str_cls = unicode
except (NameError):
    str_cls = str

import sublime

from .sys_path import st_dir
from .clear_directory import delete_directory
from .console_write import console_write
from .package_disabler import PackageDisabler



packages_dir = path.join(st_dir, u'Packages')
installed_packages_dir = path.join(st_dir, u'Installed Packages')


loader_package_name = u'0_package_control_loader'
if sys.version_info < (3,):
    loader_package_path = path.join(packages_dir, loader_package_name)
else:
    loader_package_path = path.join(installed_packages_dir, u'%s.sublime-package' % loader_package_name)


def add(priority, name, code=None):
    """
    Adds a dependency to the loader

    :param priority:
        A two-digit string. If a dep has no dependencies, this can be
        something like '01'. If it does, use something like '10' leaving
        space for other entries

    :param name:
        The name of the dependency as a unicode string

    :param code:
        Any special loader code, otherwise the default will be used
    """

    if not code:
        code = """
            from package_control import sys_path
            sys_path.add_dependency(%s)
        """ % repr(name)
        code = dedent(code)

    loader_filename = '%s-%s.py' % (priority, name)

    just_created_loader = False

    if sys.version_info < (3,):
        if not path.exists(loader_package_path):
            just_created_loader = True
            os.mkdir(loader_package_path, 0o755)

        loader_path = path.join(loader_package_path, loader_filename)
        with open(loader_path, 'wb') as f:
            f.write(code.encode('utf-8'))

    else:
        mode = 'a' if os.path.exists(loader_package_path) else 'w'
        with zipfile.ZipFile(loader_package_path, mode) as z:
            if mode == 'w':
                just_created_loader = True
                metadata = {
                    "version": "1.0.0",
                    "sublime_text": "*",
                    # Tie the loader to the platform so we can detect
                    # people syncing packages incorrectly.
                    "platforms": [sublime.platform()],
                    "url": "https://github.com/wbond/package_control/issues",
                    "description": "Package Control dependency loader"
                }
                z.writestr('dependency-metadata.json', json.dumps(metadata).encode('utf-8'))
            z.writestr(loader_filename, code.encode('utf-8'))

    # Clean things up for people who were tracking the master branch
    if just_created_loader:
        old_loader_sp = path.join(installed_packages_dir, '0-package_control_loader.sublime-package')
        old_loader_dir = path.join(packages_dir, '0-package_control_loader')

        removed_old_loader = False

        if path.exists(old_loader_sp):
            removed_old_loader = True
            os.remove(old_loader_sp)

        if path.exists(old_loader_dir):
            removed_old_loader = True
            delete_directory(old_loader_dir)

        if removed_old_loader:
            console_write(u'Cleaning up remenants of old loaders', True)

            for name in ['bz2', 'ssl-linux', 'ssl-windows']:
                dep_dir = path.join(packages_dir, name)
                if path.exists(dep_dir):
                    delete_directory(dep_dir)


def remove(name):
    """
    Removes a loader by name

    :param name:
        The name of the dependency
    """

    if not path.exists(loader_package_path):
        return

    loader_filename_regex = u'^\\d\\d-%s.py$' % re.escape(name)

    if sys.version_info < (3,):
        for filename in os.listdir(loader_package_path):
            if re.match(loader_filename_regex, filename):
                os.remove(path.join(loader_package_path, filename))
        return

    removed = False

    try:
        # With the zipfile module there is no way to delete a file, so we
        # must instead copy the other files to a new zipfile and swap the
        # filenames
        new_loader_package_path = loader_package_path + u'-new'
        old_loader_z = zipfile.ZipFile(loader_package_path, 'r')
        new_loader_z = zipfile.ZipFile(new_loader_package_path, 'w')
        for enc_filename in old_loader_z.namelist():
            if not isinstance(enc_filename, str_cls):
                filename = enc_filename.decode('utf-8')
            else:
                filename = enc_filename
            if re.match(loader_filename_regex, filename):
                removed = True
                continue
            new_loader_z.writestr(enc_filename, old_loader_z.read(enc_filename))

    finally:
        old_loader_z.close()
        new_loader_z.close()

    if not removed:
        os.remove(new_loader_package_path)
        return

    disabler = PackageDisabler()
    disabler.disable_package(loader_package_name)

    def do_swap():
        os.remove(loader_package_path)
        os.rename(new_loader_package_path, loader_package_path)
        sublime.set_timeout(lambda: disabler.reenable_package(loader_package_name), 10)
    sublime.set_timeout(do_swap, 700)
