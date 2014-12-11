import sys
import os
import re
import json
from os import path
import zipfile
import shutil
from textwrap import dedent

try:
    str_cls = unicode
except (NameError):
    str_cls = str

import sublime

from .sys_path import st_dir
from .console_write import console_write
from .package_disabler import PackageDisabler
from .settings import pc_settings_filename, load_list_setting, save_list_setting



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

    loader_metadata = metadata = {
        "version": "1.0.0",
        "sublime_text": "*",
        # Tie the loader to the platform so we can detect
        # people syncing packages incorrectly.
        "platforms": [sublime.platform()],
        "url": "https://github.com/wbond/package_control/issues",
        "description": "Package Control dependency loader"
    }
    loader_metadata_enc = json.dumps(loader_metadata).encode('utf-8')

    if sys.version_info < (3,):
        if not path.exists(loader_package_path):
            just_created_loader = True
            os.mkdir(loader_package_path, 0o755)
            with open(path.join(loader_package_path, 'dependency-metadata.json'), 'wb') as f:
                f.write(loader_metadata_enc)

        loader_path = path.join(loader_package_path, loader_filename)
        with open(loader_path, 'wb') as f:
            f.write(code.encode('utf-8'))

    else:
        mode = 'a' if os.path.exists(loader_package_path) else 'w'
        with zipfile.ZipFile(loader_package_path, mode) as z:
            if mode == 'w':
                just_created_loader = True
                z.writestr('dependency-metadata.json', loader_metadata_enc)
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
            try:
                shutil.rmtree(old_loader_dir)
            except (OSError):
                open(os.path.join(old_loader_dir, 'package-control.cleanup'), 'w').close()

        if removed_old_loader:
            console_write(u'Cleaning up remenants of old loaders', True)

            pc_settings = sublime.load_settings(pc_settings_filename())
            orig_installed_packages = load_list_setting(pc_settings, 'installed_packages')
            installed_packages = list(orig_installed_packages)

            if '0-package_control_loader' in installed_packages:
                installed_packages.remove('0-package_control_loader')

            for name in ['bz2', 'ssl-linux', 'ssl-windows']:
                dep_dir = path.join(packages_dir, name)
                if path.exists(dep_dir):
                    try:
                        shutil.rmtree(dep_dir)
                    except (OSError):
                        open(os.path.join(dep_dir, 'package-control.cleanup'), 'w').close()
                if name in installed_packages:
                    installed_packages.remove(name)

            save_list_setting(pc_settings, pc_settings_filename(),
                'installed_packages', installed_packages, orig_installed_packages)


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
