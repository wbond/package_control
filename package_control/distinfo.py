import base64
import hashlib
import os
import sys

from . import __version__ as pc_version
from . import pep440
from . import sys_path


def _trim_segments(rel_path, segments):
    """
    Trim a relative path to a specific number of segments

    :param rel_path:
        A unicode string of a relative path

    :param segments:
        An integer of the number of segments to retain

    :return:
        The relative path, trimmed to the number of segments
    """

    return "/".join(rel_path.split("/")[0:segments])


def _verify_file(abs_path, hash_, size):
    """
    Verifies a file hasn't been modified using the filesize and SHA256 hash

    :param abs_path:
        A unicode string of the absolute filesystem path

    :param hash_:
        A unicode string of the results of the SHA256 digest being passed to
        base64.urlsafe_b64encode() with any trailing equal signs truncated.

    :param size:
        An integer of the file size in bytes

    :return:
        A bool indicating if the file contents matched the hash and size
    """

    disk_size = os.path.getsize(abs_path)
    if disk_size != size:
        return False
    with open(abs_path, "rb") as f:
        digest = hashlib.sha256(f.read()).digest()
        sha = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
    if sha != hash_:
        return False
    return True


class RecordInfo:
    """
    This class describes a the content of a /RECORD line.
    """

    __slots__ = ["relative_path", "absolute_path", "size", "sha256"]

    def __init__(self, rel_path, abs_path, size, sha256):
        self.relative_path = rel_path
        self.absolute_path = abs_path
        self.size = size
        self.sha256 = sha256

    def __eq__(self, rhs):
        if self.relative_path != rhs.relative_path:
            return False
        if self.absolute_path != rhs.absolute_path:
            return False
        if self.size != rhs.size:
            return False
        if self.sha256 != rhs.sha256:
            return False
        return True

    def __hash__(self):
        return hash((self.relative_path, self.absolute_path, self.size, self.sha256))


class DistInfoNotFoundError(FileNotFoundError):
    """
    This class describes a .dist-info directory not found error.
    """

    pass


class DistInfoDir:
    """
    This class describes a .dist-info directory.

    Example: 'pyyaml-5.1.1.dist-info'

    It is used to access information stored in the directory as they were
    normal class attributes. It is an I/O driver to handle all filesystem
    operations required to read or write meta data of a library.
    """

    __slots__ = ["install_root", "dir_name"]

    def __init__(self, install_root, dist_info_dir):
        """
        Constructs a new instance.

        :param install_root:
            An unicode string of an absolute path of the directory libraries are
            installed in

        :param dist_info_dir:
            The name of a library's .dist-info directory.

            Example: 'pyyaml-5.1.1.dist-info'
        """

        self.install_root = install_root
        self.dir_name = dist_info_dir

    @property
    def path(self):
        """
        Return the absolute path of the distinfo directory on filesystem.
        """
        return os.path.join(self.install_root, self.dir_name)

    def exists(self):
        """
        Check whether .dist-info directory exists on filesystem.

        :returns:   True if the distance info directory exists.
        :rtype:     bool
        """

        return os.path.isdir(self.path)

    def ensure_exists(self):
        """
        Create the .dist-info directory if it doesn't exist on filesystem.
        """

        os.makedirs(self.path, exist_ok=True)

    @staticmethod
    def generate_wheel(python_version, plat_specific):
        """
        Generates the .dist-info/WHEEL file contents

        :param python_version:
            None if no specific version, otherwise a unicode string of "3.3" or "3.8"

        :param plat_specific:
            If the package includes a shared library or executable that is
            specific to a platform and optionally architecture
        """

        if python_version is not None and python_version not in ("3.3", "3.8", "3.13"):
            raise ValueError("Invalid python_version %s" % repr(python_version))

        version_tag = "py3"
        if python_version is not None:
            version_tag = "py" + python_version.replace(".", "")
        abi_tag = "none"
        arch_tag = "any"
        if python_version is not None and plat_specific is not False:
            abi_tag = "cp" + python_version.replace(".", "") + "m"
            if sys.platform == "darwin":
                arch = os.uname()[4]
                if python_version == "3.3":
                    arch_tag = "macosx_10_7_%s" % arch
                elif python_version == "3.8":
                    arch_tag = "macosx_10_9_%s" % arch
                elif python_version == "3.13":
                    arch_tag = "macosx_10_13_%s" % arch
            elif sys.platform == "linux":
                arch_tag = "linux_%s" % os.uname()[4]
            else:
                if sys.maxsize == 2147483647:
                    arch_tag = "win32"
                else:
                    arch_tag = "win_amd64"
        tag = "%s-%s-%s" % (version_tag, abi_tag, arch_tag)

        output = "Wheel-Version: 1.0\n"
        output += "Generator: Package Control (%s)\n" % pc_version
        output += "Root-Is-Purelib: true\n"
        output += "Tag: %s\n" % tag
        return output

    def generate_metadata(self, name, version, desc, homepage):
        """
        Generates the .dist-info/METADATA file contents

        :param name:
            The unicode string of the package name

        :param version:
            An unicode string of the version

        :param desc:
            An optional unicode string of a description

        :param homepage:
            An optional unicode string of the URL to the homepage
        """

        output = "Metadata-Version: 2.1\n"
        output += "Name: %s\n" % name
        output += "Version: %s\n" % version
        if isinstance(desc, str):
            output += "Summary: %s\n" % desc.replace("\n", " ")
        if isinstance(homepage, str):
            output += "Home-page: %s\n" % homepage

        return output

    def generate_installer(self):
        """
        Generates the .dist-info/INSTALLER file contents
        """

        return "Package Control\n"

    def add_installer_to_record(self):
        R"""
        Add INSTALLER entry to .dist-info/RECORD file.

        Note: hash has been pre-compiled using...

        ```py
        digest = hashlib.sha256("Package Control\n".encode("utf-8")).digest()
        sha = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
        ```
        """
        installer = self.dir_name + "/INSTALLER,"
        record = self.abs_path("RECORD")

        # make sure not to add duplicate entries
        with open(record, "r", encoding="utf-8") as fobj:
            items = [item for item in fobj.readlines() if not item.startswith(installer)]
            items.append(installer + "sha256=Hg_Q6w_I4zpFfb6C24LQdd4oTAMHJZDk9gtuV2yOgkw,16\n")

        with open(record, "w", encoding="utf-8", newline="\n") as fobj:
            fobj.writelines(sorted(items))

    def generate_record(self, package_dirs, package_files):
        """
        Generates the .dist-info/RECORD file contents

        :param package_dirs:
            A list of unicode strings of the package dirs

        :param package_files:
            A list of unicode strings of files not in a dir
        """

        entries = []

        def _unix_path(path):
            if os.name == "nt":
                return path.replace("\\", "/")
            return path

        def _entry(rel_path):
            fpath = os.path.join(self.install_root, rel_path)
            size = os.stat(fpath).st_size
            with open(fpath, "rb") as f:
                digest = hashlib.sha256(f.read()).digest()
                sha = base64.urlsafe_b64encode(digest).rstrip(b"=")
            return (_unix_path(rel_path), "sha256=%s" % sha.decode("utf-8"), str(size))

        for fname in os.listdir(self.path):
            rel_path = os.path.join(self.dir_name, fname)
            if fname == "RECORD":
                entries.append((_unix_path(rel_path), "", ""))
            else:
                entries.append(_entry(rel_path))

        for package_dir in package_dirs:
            for root, _, files in os.walk(os.path.join(self.install_root, package_dir)):
                for f in files:
                    path = os.path.join(root, f)
                    rel_path = os.path.relpath(path, self.install_root)
                    entries.append(_entry(rel_path))

        for f in package_files:
            entries.append(_entry(f))

        output = ""
        for e in sorted(entries, key=lambda e: e[0]):
            output += ",".join(e) + "\n"

        return output

    @staticmethod
    def extra_files():
        """
        :return:
            A set of unicode strings containing "important" files in a library
            archive that should be relocated into the .dist-info directory to
            prevent dependencies overwriting each other in the lib folder
        """

        return {
            # Files that may contain legal info
            "copying",
            "copying.txt",
            "license",
            "license.md",
            "license.txt",
            "notice",
            "patents",
            # Other general metadata files
            "authors",
            "authors.rst",
            "authors.txt",
            "changelog",
            "changelog.rst",
            "changes",
            "changes.rst",
            "contributors",
            "readme",
            "readme.md",
            "readme.rst",
            "readme.txt",
            "releasing",
            "news",
            "news.txt",
            "notes",
            "notes.rst",
        }

    @staticmethod
    def shared_lib_extensions():
        """
        :return:
            A set of unicode strings of file extensions for files that are shared
            libraries
        """

        return {".dll", ".pyd", ".so", ".dylib"}

    def abs_path(self, file_name):
        """
        Create an absolute path of a file contained in the .dist-info dir.

        :param file_name:
            An unicode string of the file name to return the absolute path for.

        :returns:
            An unicode string of the absolute path of the given file.
        """

        return os.path.join(self.install_root, self.dir_name, file_name)

    def read_metadata(self):
        """
        Read the .dist-info/METADATA file contents

        :returns:
            A dictionary with lower case keys.
        """

        with open(self.abs_path("METADATA"), "r", encoding="utf-8") as fobj:
            entries = {}
            for line in fobj.readlines():
                try:
                    key, value = line.split(": ", 1)
                    entries[key.strip().lower()] = value.strip()
                except ValueError:
                    break
            return entries

    def write_metadata(self, name, version, desc, homepage):
        """
        Read the .dist-info/METADATA file contents

        :param name:
            The unicode string of the package name

        :param version:
            An unicode string of the version

        :param desc:
            An optional unicode string of a description

        :param homepage:
            An optional unicode string of the URL to the homepage
        """

        contents = self.generate_metadata(name, version, desc, homepage)
        with open(self.abs_path("METADATA"), "w", encoding="utf-8", newline="\n") as fobj:
            fobj.write(contents)

    def read_installer(self):
        """
        Read the .dist-info/INSTALLER file contents

        :returns:
            An unicode string of of which installer was used.
        """
        try:
            with open(self.abs_path("INSTALLER"), "r", encoding="utf-8") as fobj:
                return fobj.readline().strip()
        except FileNotFoundError:
            return ""

    def write_installer(self):
        """
        Write the .dist-info/INSTALLER file contents
        """

        contents = self.generate_installer()
        with open(self.abs_path("INSTALLER"), "w", encoding="utf-8", newline="\n") as fobj:
            fobj.write(contents)

    def read_record(self):
        """
        Read the .dist-info/RECORD file contents

        :returns:
            A list of RecordInfo objects
        """

        with open(self.abs_path("RECORD"), "r", encoding="utf-8") as fobj:
            entries = []
            for line in fobj.readlines():
                line = line.strip()
                elements = line.split(",")
                if len(elements) != 3:
                    raise ValueError("Invalid record entry: %s" % line)
                is_record_path = elements[0] == self.dir_name + "/RECORD"
                if not elements[1].startswith("sha256=") and not is_record_path:
                    raise ValueError("Unabled to parse sha256 hash: %s" % line)
                ri = RecordInfo(
                    elements[0],
                    sys_path.longpath(os.path.join(self.install_root, elements[0])),
                    int(elements[2]) if not is_record_path else None,
                    elements[1][7:] if not is_record_path else None,
                )
                entries.append(ri)
            return entries

    def top_level_paths(self):
        """
        Returns a list of top-level relative paths

        :return:
            A list of paths relative to self.install_root
        """

        paths = {}
        min_level = 500
        for ri in self.read_record():
            if ri.relative_path.endswith("/"):
                level = ri.relative_path.rstrip("/").count("/")
            else:
                level = ri.relative_path.count("/")

            if level < min_level:
                min_level = level

            path_seg = ri.relative_path
            if level > min_level:
                path_seg = _trim_segments(path_seg, min_level + 1)

            while True:
                num_levels = path_seg.count("/")
                if num_levels <= min_level:
                    if num_levels not in paths:
                        paths[num_levels] = set()
                    paths[num_levels].add(path_seg)
                if num_levels == 0:
                    break
                path_seg = _trim_segments(path_seg, num_levels)

        return sorted(paths[0])

    def write_record(self, package_dirs, package_files):
        """
        Write the .dist-info/RECORD file contents

        :param package_dirs:
            A list of unicode strings of the package dirs, or None if there is no dir

        :param package_files:
            A list of unicode strings of files not in a dir
        """

        # Create an empty file so it shows up in its own file list
        record_path = self.abs_path("RECORD")
        open(record_path, "wb").close()
        contents = self.generate_record(package_dirs, package_files)
        with open(record_path, "w", encoding="utf-8", newline="\n") as fobj:
            fobj.write(contents)

    def has_wheel(self):
        """
        Check if .dist-info/WHEEL file exists

        :returns:
            `True`, if WHEEL file exists, `False` otherwise.
        """
        return os.path.isfile(self.abs_path("WHEEL"))

    def read_wheel(self):
        """
        Read the .dist-info/WHEEL file contents

        :returns:
            A dictionary with lower case keys.
        """

        with open(self.abs_path("WHEEL"), "r", encoding="utf-8") as fobj:
            entries = {}
            for line in fobj.readlines():
                key, value = line.split(": ")
                entries[key.strip().lower()] = value.strip()
            return entries

    def write_wheel(self, python_version, plat_specific):
        """
        Write the .dist-info/WHEEL file contents

        :param python_version:
            None if no specific version, otherwise a unicode string of "3.3" or "3.8"

        :param plat_specific:
            If the package includes a shared library or executable that is
            specific to a platform and optionally architecture
        """

        contents = self.generate_wheel(python_version, plat_specific)
        with open(self.abs_path("WHEEL"), "w", encoding="utf-8", newline="\n") as fobj:
            fobj.write(contents)

    def verify_python_version(self, python_version):
        """
        Ensures the package is compatible with the specified version of Python

        :param python_version:
            A unicode string of "3.3" or "3.8"
        """

        metadata = self.read_metadata()
        if metadata is False:
            return

        version_specifier = metadata.get("requires-python")
        if not version_specifier:
            return

        python_version = pep440.PEP440Version(python_version)

        for specifier in version_specifier.split(","):
            if not pep440.check_version(specifier, python_version):
                raise EnvironmentError(
                    'The library "{}" is not compatible with Python {}'.format(metadata["name"], python_version)
                )

    def verify_files(self, missing_ok=False):
        """
        Returns two sets of paths

        :param missing_ok:
            If `True` treat missing files as unmodified.

        :return:
            A 2-element tuple:
             0: A set of RecordInfo object that are unmodified
             1: A set of RecordInfo objects that are modified
        """

        unmodified_paths = set()
        modified_paths = set()
        for ri in self.read_record():
            # The RECORD file itself doesn't have a sha or filesize
            if ri.relative_path == self.dir_name + "/RECORD":
                unmodified_paths.add(ri)
                continue
            try:
                ok = _verify_file(ri.absolute_path, ri.sha256, ri.size)
            except FileNotFoundError:
                ok = missing_ok
            if ok:
                unmodified_paths.add(ri)
            else:
                modified_paths.add(ri)
        return (unmodified_paths, modified_paths)
