import os
import re
import shutil

import sublime

from . import sys_path
from .distinfo import DistInfoDir, find_dist_info_dir


class Library:

    __slots__ = ['name', 'python_version']

    def __init__(self, name, python_version):
        if not isinstance(name, str):
            raise TypeError("name must be a unicode string")
        if not name:
            raise ValueError("name must not be empty")

        if not isinstance(python_version, str):
            raise TypeError("python_version must be a unicode string")
        if python_version not in set(["3.3", "3.8"]):
            raise ValueError("python_version must be \"3.3\" or \"3.8\", not %r" % python_version)

        self.name = name
        self.python_version = python_version

    def __repr__(self):
        return "Library(%r, %r)" % (self.name, self.python_version)

    def _to_tuple(self, lower=False):
        return (self.name.lower() if lower else self.name, self.python_version)

    def __hash__(self):
        return hash(self._to_tuple())

    def __eq__(self, rhs):
        return self._to_tuple() == rhs._to_tuple()

    def __ne__(self, rhs):
        return self._to_tuple() != rhs._to_tuple()

    def __lt__(self, rhs):
        """
        Default sorting is case insensitive
        """

        self_lt = self._to_tuple(lower=True)
        rhs_lt = self._to_tuple(lower=True)
        if self_lt == rhs_lt:
            return self._to_tuple() < rhs._to_tuple()
        return self_lt < rhs_lt

    @property
    def path(self):
        return os.path.join(sys_path.lib_paths()[self.python_version], self.name)


def _name_from_dist_info_dirname(dirname):
    library_name = dirname[:-10]
    return re.sub(
        r'-(?:'
        r'(\d+(?:\.\d+)*)'
        r'([-._]?(?:alpha|a|beta|b|preview|pre|c|rc)\.?\d*)?'
        r'(-\d+|(?:[-._]?(?:rev|r|post)\.?\d*))?'
        r'([-._]?dev\.?\d*)?'
        r')$',
        '',
        library_name,
        count=1
    )


def list_all():
    """
    List all dependencies installed

    :return:
        A list of Library() object
    """

    out = []
    for python_version in ("3.3", "3.8"):
        install_root = sys_path.lib_paths()[python_version]
        for fname in os.listdir(install_root):
            if not fname.endswith(".dist-info"):
                continue
            path = os.path.join(install_root, fname)
            if not os.path.isdir(path):
                continue
            record_path = os.path.join(path, 'RECORD')
            if not os.path.isfile(record_path):
                continue
            out.append(Library(
                _name_from_dist_info_dirname(fname),
                python_version
            ))
    return sorted(out)


def list_unmanaged():
    """
    List all dependencies installed that Package Control didn't install

    :return:
        A list of Library() objects
    """

    out = []
    for python_version in ("3.3", "3.8"):
        install_root = sys_path.lib_paths()[python_version]
        for fname in os.listdir(install_root):
            if not fname.endswith(".dist-info"):
                continue
            path = os.path.join(install_root, fname)
            if not os.path.isdir(path):
                continue
            installer_path = os.path.join(path, 'INSTALLER')
            if not os.path.isfile(installer_path):
                continue

            # We ignore what we've installed since we want unmanaged libraries
            with open(installer_path, 'r', encoding='utf-8') as f:
                if f.read().strip().startswith('Package Control'):
                    continue

            out.append(Library(
                _name_from_dist_info_dirname(fname),
                python_version
            ))
    return out


def convert_dependency(dependency_path, python_version, name, version, description, url):
    """
    Modifies a directory containing an old-style dependency into a library,
    in-place. This adds the .dist-info dir inside of the dependency_path
    so that the top-level files and dirs can be copied to the final
    destination.

    :param dependency_path:
        A unicode path the dependency was installed or extracted into.
        This directory will contain one of the following folders:
         - "all"
         - "st3"
         - "st3_{OS}"
         - "st3_{OS}_{ARCH}"

    :param python_version:
        A unicode string of "3.3" or "3.8"

    :param name:
        A unicode string of the library name

    :param version:
        A unicode string of a PEP 440 version

    :param description:
        An optional unicode string of a description of the library

    :param url:
        An optional unicode string of the homepage for the library
    """

    ver = 'st3'
    plat = sublime.platform()
    arch = sublime.arch()

    install_rel_paths = {
        'all': 'all',
        'ver': ver,
        'plat': '%s_%s' % (ver, plat),
        'arch': '%s_%s_%s' % (ver, plat, arch)
    }

    src_dir = None
    plat_specific = False
    for variant in ('arch', 'plat', 'ver', 'all'):
        install_path = os.path.join(dependency_path, install_rel_paths[variant])
        if os.path.exists(install_path):
            src_dir = install_path
            plat_specific = variant in ('arch', 'plat')
            break

    if not src_dir:
        raise ValueError('Unrecognized source archive layout')

    did_name = '%s-%s.dist-info' % (name, version)
    did = DistInfoDir(src_dir, did_name)
    did.ensure_exists()
    did.write_metadata(name, version, description, url)
    did.write_installer()
    did.write_wheel(python_version, plat_specific)

    extra_filenames = did.extra_files()
    shared_exts = did.shared_lib_extensions()

    # We filter the list of files in dependencies to remove things like
    # .sublime-* files since they aren't supported when located in the
    # library folder.
    package_dirs = []
    package_files = []
    for fname in os.listdir(src_dir):
        path = os.path.join(src_dir, fname)
        ext = os.path.splitext(fname)[-1]
        lf = fname.lower()
        if os.path.isdir(path):
            package_dirs.append(fname)
        elif ext in {'.py', '.pyc'}:
            package_files.append(fname)
        elif ext in shared_exts:
            package_files.append(fname)
        elif lf in extra_filenames:
            # Extra files in the root need to be put into the
            # .dist-info dir since that is the only place we can
            # ensure there won't be name conflicts
            new_path = os.path.join(src_dir, did_name, fname)
            shutil.copy(path, new_path)
            # We don't add the paths to package_files, since the RECORD
            # automatically includes everything in the .dist-info dir

    # Also look in the root of the package for the extra files since most
    # dependencies put the files there
    for fname in os.listdir(dependency_path):
        if fname.lower() in extra_filenames:
            path = os.path.join(dependency_path, fname)
            new_path = os.path.join(src_dir, did_name, fname)
            shutil.copy(path, new_path)

    did.write_record(package_dirs, package_files)

    return did


def install(dist_info, new_install_root):
    """
    :param dist_info:
        A distinfo.DistInfoDir() object of the package to install

    :param new_install_root:
        A unicode path to the directory to move the dist_info into
    """

    for rel_path in dist_info.top_level_paths():
        src_path = os.path.join(dist_info.install_root, rel_path)
        dest_path = os.path.join(new_install_root, rel_path)
        dest_parent = os.path.dirname(dest_path)
        if not os.path.exists(dest_parent):
            os.makedirs(dest_parent)
        # shutil.move() will nest folders if the destination exists already
        if os.path.isdir(src_path):
            if os.path.exists(dest_path):
                os.rmdir(dest_path)
            dest_path = dest_parent
        shutil.move(src_path, dest_path)


def remove(install_root, name):
    """
    Deletes all of the files from a library

    :param install_root:
        A unicode string of directory libraries are installed in

    :param name:
        A unicode string of the library name

    :raises:
        OSError - when a permission error occurs trying to remove a file
    """

    dist_info = find_dist_info_dir(install_root, name)

    for rel_path in dist_info.top_level_paths():
        # Remove the .dist-info dir last so we have info for cleanup in case
        # we hit an error along the way
        if rel_path == dist_info.dir_name:
            continue

        abs_path = os.path.join(dist_info.install_root, rel_path)

        if not os.path.exists(abs_path):
            continue

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.unlink(abs_path)

    abs_path = os.path.join(dist_info.install_root, dist_info.dir_name)
    if os.path.exists(abs_path):
        shutil.rmtree(abs_path)


def _pep440_to_tuple(version_string):
    """
    Constructs a tuple of integers that allows comparing valid PEP440 versions

    :param version_string:
        A unicode PEP440 version string

    :return:
        A tuple of integers
    """

    match = re.search(
        r'(?:(\d+)\!)?'
        r'(\d+(?:\.\d+)*)'
        r'([-._]?(?:alpha|a|beta|b|preview|pre|c|rc)\.?\d*)?'
        r'(-\d+|(?:[-._]?(?:rev|r|post)\.?\d*))?'
        r'([-._]?dev\.?\d*)?',
        version_string
    )
    if not match:
        return tuple()

    epoch = match.group(1)
    if epoch:
        epoch = int(epoch)
    else:
        epoch = 0

    nums = tuple(map(int, match.group(2).split('.')))

    pre = match.group(3)
    if pre:
        pre = pre.replace('alpha', 'a')
        pre = pre.replace('beta', 'b')
        pre = pre.replace('preview', 'rc')
        pre = pre.replace('pre', 'rc')
        pre = re.sub(r'(?<!r)c', 'rc', pre)
        pre = pre.lstrip('._-')
        pre_dig_match = re.search(r'\d+', pre)
        if pre_dig_match:
            pre_dig = int(pre_dig_match.group(0))
        else:
            pre_dig = 0
        pre = pre.rstrip('0123456789')

        pre_num = {
            'a': -3,
            'b': -2,
            'rc': -1,
        }[pre]

        pre_tup = (pre_num, pre_dig)
    else:
        pre_tup = tuple()

    post = match.group(4)
    if post:
        post_dig_match = re.search(r'\d+', post)
        if post_dig_match:
            post_dig = int(post_dig_match.group(0))
        else:
            post_dig = 0
        post_tup = (1, post_dig)
    else:
        post_tup = tuple()

    dev = match.group(5)
    if dev:
        dev_dig_match = re.search(r'\d+', dev)
        if dev_dig_match:
            dev_dig = int(dev_dig_match.group(0))
        else:
            dev_dig = 0
        dev_tup = (-4, dev_dig)
    else:
        dev_tup = tuple()

    normalized = [epoch, nums]
    if pre_tup:
        normalized.append(pre_tup)
    if post_tup:
        normalized.append(post_tup)
    if dev_tup:
        normalized.append(dev_tup)
    # This ensures regular releases happen after dev and prerelease, but
    # before post releases
    if not pre_tup and not post_tup and not dev_tup:
        normalized.append((0, 0))

    return tuple(normalized)


def _norm_tup(a, b):
    while len(a) < len(b):
        a = a + ((0,),)
    while len(a) > len(b):
        b = b + ((0,),)

    for i in range(1, len(a)):
        while len(a[i]) < len(b[i]):
            a = a[:i] + (a[i] + (0,),) + a[i + 1:]
        while len(a[i]) > len(b[i]):
            b = b[:i] + (b[i] + (0,),) + b[i + 1:]

    return a, b


class PEP440Version:
    string = ''
    tup = tuple()

    def __init__(self, string):
        self.string = string
        self.tup = _pep440_to_tuple(string)

    def __str__(self):
        return self.string

    def __repr__(self):
        return 'PEP440Version(' + repr(self.string) + ')'

    def __eq__(self, rhs):
        a, b = _norm_tup(self.tup, rhs.tup)
        return a == b

    def __ne__(self, rhs):
        a, b = _norm_tup(self.tup, rhs.tup)
        return a != b

    def __lt__(self, rhs):
        a, b = _norm_tup(self.tup, rhs.tup)
        return a < b

    def __le__(self, rhs):
        a, b = _norm_tup(self.tup, rhs.tup)
        return a <= b

    def __gt__(self, rhs):
        a, b = _norm_tup(self.tup, rhs.tup)
        return a > b

    def __ge__(self, rhs):
        a, b = _norm_tup(self.tup, rhs.tup)
        return a >= b

    def __hash__(self):
        return hash(self.string)
