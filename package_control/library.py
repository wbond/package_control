import os
import shutil

import sublime

from . import sys_path
from . import distinfo
from .clear_directory import delete_directory


class Library:
    __slots__ = ['name', 'python_version']

    def __init__(self, name, python_version):
        if not isinstance(name, str):
            raise TypeError("name must be a unicode string")
        if not name:
            raise ValueError("name must not be empty")

        if not isinstance(python_version, str):
            raise TypeError("python_version must be a unicode string")
        if python_version not in sys_path.lib_paths():
            raise ValueError("python_version must be one of %s, not %r" % (
                list(sys_path.lib_paths().keys()), python_version)
            )

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


class InstalledLibrary(Library):
    __slots__ = ['dist_info']

    def __init__(self, dist_info_dir, python_version):
        self.dist_info = distinfo.DistInfoDir(sys_path.lib_paths()[python_version], dist_info_dir)
        super().__init__(self.dist_info.library_name, python_version)


def list_all():
    """
    List all dependencies installed

    :return:
        A set of InstalledLibrary() object
    """

    out = set()
    for python_version, install_root in sys_path.lib_paths().items():
        for fname in os.listdir(install_root):
            if not fname.endswith(".dist-info"):
                continue
            record_path = os.path.join(install_root, fname, 'RECORD')
            if not os.path.isfile(record_path):
                continue
            out.add(InstalledLibrary(fname, python_version))

    return out


def list_unmanaged():
    """
    List all dependencies installed that Package Control didn't install

    :return:
        A set of InstalledLibrary() objects
    """

    out = set()
    for python_version, install_root in sys_path.lib_paths().items():
        for fname in os.listdir(install_root):
            if not fname.endswith(".dist-info"):
                continue
            installer_path = os.path.join(install_root, fname, 'INSTALLER')
            if not os.path.isfile(installer_path):
                continue

            # We ignore what we've installed since we want unmanaged libraries
            with open(installer_path, 'r', encoding='utf-8') as f:
                if f.read().strip().startswith('Package Control'):
                    continue

            out.add(InstalledLibrary(fname, python_version))

    return out


def find_installed(lib):
    """
    Find a library by name in given directory.

    :param library_name:
        An unicode string of the library name

    :param python_version:
        A unicode string of "3.3" or "3.8"

    returns:
        An InstalledLibrary() object
    """

    install_root = sys_path.lib_paths()[lib.python_version]
    for fname in os.listdir(install_root):
        if lib.name == distinfo.library_name_from_dist_info_dirname(fname):
            return InstalledLibrary(fname, lib.python_version)
    return None


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
         - "st4"
         - "st4_{PY}"
         - "st4_{PY}_{OS}"
         - "st4_{PY}_{OS}_{ARCH}"

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

    py = python_version.replace(".", "")
    plat = sublime.platform()
    arch = sublime.arch()

    install_rel_paths = []

    # include st4 dependencies on ST4, only
    if int(sublime.version()) >= 4000:
        install_rel_paths.append(('st4_arch', 'st4_py%s_%s_%s' % (py, plat, arch)))
        install_rel_paths.append(('st4_plat', 'st4_py%s_%s' % (py, plat)))
        install_rel_paths.append(('st4_py', 'st4_py%s' % py))
        install_rel_paths.append(('st4', 'st4'))

    # platform/arch specific st3 dependencies are most likely only compatible with python 3.3
    if python_version == "3.3":
        install_rel_paths.append(('st3_arch', 'st3_%s_%s' % (plat, arch)))
        install_rel_paths.append(('st3_plat', 'st3_%s' % plat))

    # commonly supported variants
    install_rel_paths.append(('st3', 'st3'))
    install_rel_paths.append(('all', 'all'))

    # Find source paths
    # 1. Begin with st4 and fallback to st3 dependencies.
    # 2. Begin with most specific followed by more generic variants.
    src_dir = None
    plat_specific = False
    for variant, rel_path in install_rel_paths:
        install_path = os.path.join(dependency_path, rel_path)
        if os.path.exists(install_path):
            src_dir = install_path
            plat_specific = variant in ('st3_arch', 'st3_plat', 'st4_arch', 'st4_plat')
            break

    if not src_dir:
        raise ValueError('Unrecognized or incompatible source archive layout')

    did_name = '%s-%s.dist-info' % (name, version)
    did = distinfo.DistInfoDir(src_dir, did_name)
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
                delete_directory(dest_path, ignore_errors=False)
            dest_path = dest_parent
        shutil.move(src_path, dest_path)


def remove(installed_library):
    """
    Deletes all of the files from a library

    :param install_root:
        A unicode string of directory libraries are installed in

    :param installed_library:
        A InstalledLibrary object representing the library to remove

    :raises:
        OSError - when a permission error occurs trying to remove a file
    """

    dist_info = installed_library.dist_info
    if not dist_info.exists():
        raise distinfo.DistInfoNotFoundError()

    # Bytecode cache directory and extension
    python_version = installed_library.python_version
    cache_dir = sys_path.python_libs_cache_path(python_version)
    cache_ext = ".cpython-{}.opt-1.pyc".format(python_version.replace(".", ""))

    for rel_path in dist_info.top_level_paths():
        # Remove the .dist-info dir last so we have info for clean-up in case
        # we hit an error along the way
        if rel_path == dist_info.dir_name:
            continue

        abs_path = os.path.join(dist_info.install_root, rel_path)

        if os.path.isdir(abs_path):
            delete_directory(abs_path, ignore_errors=False)

            # remove bytecode cache
            if cache_dir:
                delete_directory(os.path.join(cache_dir, rel_path))

        elif os.path.isfile(abs_path):
            os.remove(abs_path)

            # remove bytecode cache
            if cache_dir and abs_path.endswith(".py"):
                try:
                    os.remove(os.path.join(cache_dir, rel_path[:-3] + cache_ext))
                except OSError:
                    pass

    # remove .dist-info directory
    abs_path = os.path.join(dist_info.install_root, dist_info.dir_name)
    delete_directory(abs_path, ignore_errors=False)
