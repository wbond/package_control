import base64
import hashlib
import os
import re
import sys

from . import __version__ as pc_version

_dist_info_pattern = re.compile(
    r'''(?x)
    (?P<name>.+?)-(?P<version>
        (?P<major>[0-9]+)
      \.(?P<minor>[0-9]+)
      \.(?P<patch>[0-9]+)
      (?:\-(?P<prerelease>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?))?
      (?:\+(?P<build>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?))?
    )'''
)


def match_dist_info_dir(dir_name, library_name):
    """
    Match a given directory name against the library name.

    Distance information directories are always of the form <name>-<semver>.
    This function extracts the name part and compares it with the given
    library_name

    :param dir_name:
        An unicode string of a directory name which might be the desired
        distance information directory, representing the library.

    :param library_name:
        An unicode string of a library name, to find a distance information
        directory for.

    :returns:
        The regexp match object, if dir_name is the .dist-info directory of
        the given library or False otherwise.

        The match object provides all information the .dist-info directory
        name can offer:

        match['name']        - library name
        match['version']     - full semver version string
        match['major']       - semver part feed SemVer() with
        match['minor']       - semver part feed SemVer() with
        match['patch']       - semver part feed SemVer() with
        match['prerelease']  - semver part feed SemVer() with
        match['build']       - semver part feed SemVer() with
    """

    match = _dist_info_pattern.match(dir_name)
    if match and match['name'] == library_name:
        return match
    return False


def find_dist_info_dir(install_root, library_name):
    """
    Find the .dist-info directory for a given library.

    :param install_root:
        An unicode string of an absolute path of the directory libraries are
        installed in

    :param library_name:
        An unicode string of the library name

    :returns:
        An unicode string of the .dist-info directory.

    :raises:
        FileNotFoundError if no .dist-info directory was found.
    """

    for dir_name in os.listdir(install_root):
        if match_dist_info_dir(dir_name, library_name):
            return DistInfoDir(install_root, dir_name)
    raise FileNotFoundError('Library {} not installed!'.format(library_name))


def list_dist_info_dirs(install_root):
    """
    Generates a list of all distance information directories in the given
    installlation directory.

    :param install_root:
        An unicode string of an absolute path of the directory libraries are
        installed in

    :yields:
        DistInfoDir objects for all distance information directories.
    """

    for dir_name in os.listdir(install_root):
        if dir_name.endswith('.dist-info'):
            yield DistInfoDir(install_root, dir_name)
    return False


class DistInfoDir:
    """
    This class describes a distance information directory.

    Example: 'pyyaml-5.1.1.dist-info'

    It is used to access information stored in the directory as they were
    normal class attributes. It is an I/O driver to handle all filesystem
    operations required to read or write meta data of a library.
    """

    __slots__ = ['install_root', 'dir_name', 'dir_path']

    def __init__(self, install_root, dist_info_dir):
        """
        Constructs a new instance.

        :param install_root:
            An unicode string of an absolute path of the directory libraries are
            installed in

        :param dist_info_dir:
            The name of a library's distance information directory.

            Example: 'pyyaml-5.1.1.dist-info'
        """

        self.install_root = install_root
        self.dir_name = dist_info_dir
        self.dir_path = os.path.join(install_root, dist_info_dir)

    def exists(self):
        """
        Check whether distance info directory exists on filesystem.

        :returns:   True if the distance info directory exists.
        :rtype:     bool
        """

        return os.path.isdir(self.dir_path)

    def ensure_exists(self):
        """
        Create the distance info directory if it doesn't exist on filesystem.
        """

        os.makedirs(self.dir_path, exist_ok=True)

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

        version_tag = 'py3'
        if python_version is not None:
            version_tag = 'py' + python_version.replace('.', '')
        abi_tag = 'none'
        arch_tag = 'any'
        if python_version is not None and plat_specific is not False:
            abi_tag = 'cp' + python_version.replace('.', '') + 'm'
            if sys.platform == 'darwin':
                arch = os.uname()[4]
                if python_version == '3.3':
                    arch_tag = 'macosx_10_7_%s' % arch
                elif python_version == '3.8':
                    arch_tag = 'macosx_10_9_%s' % arch
            elif sys.platform == 'linux':
                arch_tag = 'linux_%s' % os.uname()[4]
            else:
                if sys.maxsize == 2147483647:
                    arch_tag = 'win32'
                else:
                    arch_tag = 'win_amd64'
        tag = '%s-%s-%s' % (version_tag, abi_tag, arch_tag)

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
            output += "Summary: %s\n" % desc.replace('\n', ' ')
        if isinstance(homepage, str):
            output += "Home-page: %s\n" % homepage

        return output

    def generate_installer(self):
        """
        Generates the .dist-info/INSTALLER file contents
        """

        return "Package Control\n"

    def generate_record(self, package_dirs, package_files):
        """
        Generates the .dist-info/RECORD file contents

        :param package_dirs:
            A list of unicode strings of the package dirs, or None if there is no dir

        :param package_files:
            A list of unicode strings of files not in a dir
        """

        entries = []

        def _unix_path(path):
            if os.name == 'nt':
                return path.replace('\\', '/')
            return path

        def _entry(rel_path):
            fpath = os.path.join(self.install_root, rel_path)
            size = os.stat(fpath).st_size
            with open(fpath, 'rb') as f:
                digest = hashlib.sha256(f.read()).digest()
                sha = base64.urlsafe_b64encode(digest).rstrip(b'=')
            return (_unix_path(rel_path), 'sha256=%s' % sha.decode('utf-8'), str(size))

        for fname in os.listdir(self.dir_path):
            rel_path = os.path.join(self.dir_name, fname)
            if fname == 'RECORD':
                entries.append((_unix_path(rel_path), '', ''))
            else:
                entries.append(_entry(rel_path))

        for package_dir in package_dirs:
            for root, dirs, files in os.walk(os.path.join(self.install_root, package_dir)):
                for f in files:
                    path = os.path.join(root, f)
                    rel_path = os.path.relpath(path, self.install_root)
                    entries.append(_entry(rel_path))

        for f in package_files:
            entries.append(_entry(f))

        output = ''
        for e in entries:
            output += ",".join(e) + "\n"

        return output

    @staticmethod
    def extra_files():
        """
        :return:
            A set of unicode strings containing "important" files in a library
            archive that should be relocated into the .dist-info directory to
            prevent depdencies overwriting each other in the lib folder
        """

        return {
            # Files that may contain legal info
            'copying',
            'copying.txt',
            'license',
            'license.md',
            'license.txt',
            'notice',
            'patents',
            # Other general metadata files
            'authors',
            'authors.rst',
            'authors.txt',
            'changelog',
            'changelog.rst',
            'changes',
            'changes.rst',
            'contributors',
            'readme',
            'readme.md',
            'readme.rst',
            'readme.txt',
            'releasing',
            'news',
            'news.txt',
            'notes',
            'notes.rst'
        }

    @staticmethod
    def shared_lib_extensions():
        """
        :return:
            A set of unicode strings of file extensions for files that are shared
            libraries
        """

        return {
            '.pyd',
            '.so',
            '.dylib'
        }

    def abs_path(self, file_name):
        """
        Create an absolute path of a file contained in the distance information dir.

        :param file_name:
            An unicode string of the file name to return the absolute path for.

        :returns:
            An unicode string of the absolute path of the given file.
        """

        return os.path.join(self.dir_path, file_name)

    def read_metadata(self):
        """
        Read the .dist-info/METADATA file contents

        :returns:
            A dictionary with lower case keys.
        """

        with open(self.abs_path('METADATA'), 'r', encoding='utf-8') as fobj:
            entries = {}
            for line in fobj.readlines():
                key, value = line.split(': ')
                entries[key.strip().lower()] = value.strip()
            return entries
        return False

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

        contents = self.generate_metadata(
            name,
            version,
            desc,
            homepage
        )
        with open(self.abs_path('METADATA'), 'w', encoding='utf-8') as fobj:
            fobj.write(contents)

    def read_installer(self):
        """
        Read the .dist-info/INSTALLER file contents

        :returns:
            An unicode string of of which installer was used.
        """

        with open(self.abs_path('INSTALLER'), 'r', encoding='utf-8') as fobj:
            return fobj.readline(1).strip()
        return False

    def write_installer(self):
        """
        Write the .dist-info/INSTALLER file contents
        """

        contents = self.generate_installer()
        with open(self.abs_path('INSTALLER'), 'w', encoding='utf-8') as fobj:
            fobj.write(contents)

    def read_record(self):
        """
        Read the .dist-info/RECORD file contents

        :returns:
            A list of record entries, each a list of rel_path, hash, size.
        """

        with open(self.abs_path('RECORD'), 'r', encoding='utf-8') as fobj:
            entries = []
            for line in fobj.readlines():
                entries.append(line.strip().split(','))
            return entries
        return False

    def write_record(self, package_dirs, package_files):
        """
        Write the .dist-info/RECORD file contents

        :param package_dirs:
            A list of unicode strings of the package dirs, or None if there is no dir

        :param package_files:
            A list of unicode strings of files not in a dir
        """

        # Create an empty file so it shows up in its own file list
        record_path = self.abs_path('RECORD')
        open(record_path, 'wb').close()
        contents = self.generate_record(package_dirs, package_files)
        with open(record_path, 'w', encoding='utf-8') as fobj:
            fobj.write(contents)

    def read_wheel(self):
        """
        Read the .dist-info/WHEEL file contents

        :returns:
            A dictionary with lower case keys.
        """

        with open(self.abs_path('WHEEL'), 'r', encoding='utf-8') as fobj:
            entries = {}
            for line in fobj.readlines():
                key, value = line.split(': ')
                entries[key.strip().lower()] = value.strip()
            return entries
        return False

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
        with open(self.abs_path('WHEEL'), 'w', encoding='utf-8') as fobj:
            fobj.write(contents)
