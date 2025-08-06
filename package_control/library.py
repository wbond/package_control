import os
import re
import shutil

import sublime

from . import sys_path
from . import distinfo
from .clear_directory import delete_directory

BUILTIN_LIBRARIES = {
    "3.3": {},
    "3.8": {"enum", "pathlib", "typing"},
    "3.13": {"enum", "pathlib", "typing"},
}
"""3rd-party libraries, which are part of stdlib as of certain python version"""

DEPENDENCY_NAME_MAP = {
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "python-jinja2": "Jinja2",
    "python-markdown": "Markdown",
    "python-pywin32": "pywin32",
    "python-six": "six",
    "python-toml": "toml",
    "pyyaml": "PyYAML",
    "ruamel-yaml": "ruamel.yaml",
    "serial": "pyserial",
}
"""
Most legacy dependency are simply re-packed python packages.
Some of them had been given different names, which would cause issues, when
installing them directly from pypi.org. They are therefore translated, using
the following name map. This way legacy and maybe unmaintained packages
which still request old dependencies are pointed to the new ones,
which should reduce friction when moving on to python 3.8 onwards.
"""

PEP491_NAME_PATTERN = re.compile(r"[^\w.]+", re.UNICODE)
"""PEP491 package name escape pattern."""


def escape_name(name):
    """
    Escape library name according to PEP491

    :param name:
        library name

    :returns:
        PEP491 escaped distribution name
    """
    return PEP491_NAME_PATTERN.sub("_", name)


def translate_name(name):
    """
    Translate old dependency name to real pypi library name

    :param name:
        Legacy Sublime Text dependency name

    :returns:
        PyPI complient library name.
    """
    return DEPENDENCY_NAME_MAP.get(name, name)


def names_to_libraries(names, python_version):
    """
    Convert a set of dependency names into libraries.

    :param names:
        The iteratable of possibly legacy dependency or library names.

    :param python_version:
        The python version to built the set for.

    :returns:
        A generator object of ``Library`` objects.
    """
    builtins = BUILTIN_LIBRARIES.get(python_version, set())

    for name in names:
        name = translate_name(name)
        if name not in builtins:
            yield Library(name, python_version)

    return None


class Library:
    __slots__ = ["name", "dist_name", "python_version"]

    def __init__(self, name, python_version):
        if not isinstance(name, str):
            raise TypeError("name must be a unicode string")
        if not name:
            raise ValueError("name must not be empty")

        if not isinstance(python_version, str):
            raise TypeError("python_version must be a unicode string")
        if python_version not in sys_path.lib_paths():
            raise ValueError(
                "python_version must be one of {}, not {!r}".format(
                    sys_path.python_versions(), python_version
                )
            )

        self.name = name
        self.dist_name = escape_name(self.name).lower()
        self.python_version = python_version

    def __repr__(self):
        return "{}({!r}, {!r})".format(self.__class__.__name__, self.name, self.python_version)

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self._to_tuple())

    def __eq__(self, rhs):
        return self._to_tuple() == rhs._to_tuple()

    def __ne__(self, rhs):
        return self._to_tuple() != rhs._to_tuple()

    def __gt__(self, rhs):
        return self._to_tuple() > rhs._to_tuple()

    def __lt__(self, rhs):
        return self._to_tuple() < rhs._to_tuple()

    def _to_tuple(self):
        return (self.dist_name, self.python_version)


class InstalledLibrary(Library):
    __slots__ = ["dist_info"]

    def __init__(self, install_root, dist_info_dir, python_version):
        self.dist_info = distinfo.DistInfoDir(install_root, dist_info_dir)
        self.name = self.dist_info.read_metadata()["name"]
        self.dist_name = dist_info_dir[: dist_info_dir.find("-")].lower()
        self.python_version = python_version

    def is_managed(self):
        """
        Library was installed and is therefore managed by Package Control.
        """
        return self.dist_info.read_installer() == self.dist_info.generate_installer().strip()


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
            record_path = os.path.join(install_root, fname, "RECORD")
            if not os.path.isfile(record_path):
                continue
            out.add(InstalledLibrary(install_root, fname, python_version))

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
            if not fname.lower().endswith(".dist-info"):
                continue
            installer_path = os.path.join(install_root, fname, "INSTALLER")
            if not os.path.isfile(installer_path):
                continue

            # We ignore what we've installed since we want unmanaged libraries
            with open(installer_path, "r", encoding="utf-8") as f:
                if f.read().strip().startswith("Package Control"):
                    continue

            out.add(InstalledLibrary(install_root, fname, python_version))

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
    pattern = re.compile(r"{0.dist_name}-\S+\.dist-info".format(lib), re.IGNORECASE)
    install_root = sys_path.lib_paths()[lib.python_version]
    for fname in os.listdir(install_root):
        if pattern.match(fname):
            try:
                return InstalledLibrary(install_root, fname, lib.python_version)
            except (FileNotFoundError, KeyError):
                # remove malformed dist-info dir to enforce library re-installation
                #   METADATA missing or does not contain "name"
                delete_directory(os.path.join(install_root, fname))
                break

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

    # convert legacy dependency names to official pypi package names
    name = translate_name(name)

    py = python_version.replace(".", "")
    plat = sublime.platform()
    arch = sublime.arch()

    install_rel_paths = []

    # include st4 dependencies on ST4, only
    if int(sublime.version()) >= 4000:
        # platform / arch specific releases must exactly match requested python version
        # as they are expected to contain compiled libraries
        install_rel_paths.append(("st4_arch", "st4_py{}_{}_{}".format(py, plat, arch)))
        install_rel_paths.append(("st4_plat", "st4_py{}_{}".format(py, plat)))
        # pure python releases releases for python 3.13+
        if python_version == "3.13":
            install_rel_paths.append(("st4_py", "st4_py313".format()))
        # pure python releases for python 3.8+
        install_rel_paths.append(("st4_py", "st4_py38".format()))
        install_rel_paths.append(("st4", "st4"))

    # platform/arch specific st3 dependencies are most likely only compatible with python 3.3
    if python_version == "3.3":
        install_rel_paths.append(("st3_arch", "st3_{}_{}".format(plat, arch)))
        install_rel_paths.append(("st3_plat", "st3_{}".format(plat)))

    # commonly supported variants
    install_rel_paths.append(("st3", "st3"))
    install_rel_paths.append(("all", "all"))

    # Find source paths
    # 1. Begin with st4 and fallback to st3 dependencies.
    # 2. Begin with most specific followed by more generic variants.
    src_dir = None
    plat_specific = False
    for variant, rel_path in install_rel_paths:
        install_path = os.path.join(dependency_path, rel_path)
        if os.path.exists(install_path):
            src_dir = install_path
            plat_specific = variant in ("st3_arch", "st3_plat", "st4_arch", "st4_plat")
            break

    if not src_dir:
        raise ValueError("Unrecognized or incompatible source archive layout")

    did_name = "{}-{}.dist-info".format(escape_name(name), version)
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
        elif ext in {".py", ".pyc"}:
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
        os.makedirs(dest_parent, exist_ok=True)
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
    delete_directory(dist_info.path, ignore_errors=False)
