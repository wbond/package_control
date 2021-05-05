import base64
import hashlib
import os
import sys

from . import __version__ as pc_version


def generate_wheel_file(python_version, plat_specific):
    """
    Generates the .dist-info/WHEEL file contents

    :param python_version:
        None if no specific version, otherwise a unicode string of "3.3" or
        "3.8"

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


def generate_metadata_file(name, version, desc, homepage):
    """
    Generates the .dist-info/METADATA file contents

    :param name:
        The unicode string of the package name

    :param version:
        A unicode string of the version

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


def generate_installer():
    """
    Generates the .dist-info/INSTALLER file contents
    """

    return "Package Control\n"


def generate_record(install_root, dist_info_dir, package_dirs, package_files):
    """
    Generates the .dist-info/RECORD file contents

    :param install_root:
        A unicode string of the dir the package is being installed into

    :param dist_info_dir:
        A unicode string of the .dist-info dir for the package

    :param package_dir:
        A unicode string of the package dir, or None if there is no dir

    :param package_files:
        A list of unicode strings of files not in a dir
    """

    entries = []

    def _unix_path(path):
        if os.name == 'nt':
            return path.replace('\\', '/')
        return path

    def _entry(rel_path):
        fpath = os.path.join(install_root, rel_path)
        size = os.stat(fpath).st_size
        with open(fpath, 'rb') as f:
            digest = hashlib.sha256(f.read()).digest()
            sha = base64.urlsafe_b64encode(digest).rstrip(b'=')
        return (_unix_path(rel_path), 'sha256=%s' % sha.decode('utf-8'), str(size))

    for fname in os.listdir(os.path.join(install_root, dist_info_dir)):
        rel_path = os.path.join(dist_info_dir, fname)
        if fname == 'RECORD':
            entries.append((_unix_path(rel_path), '', ''))
        else:
            entries.append(_entry(rel_path))

    for package_dir in package_dirs:
        for root, dirs, files in os.walk(os.path.join(install_root, package_dir)):
            for f in files:
                path = os.path.join(root, f)
                rel_path = os.path.relpath(path, install_root)
                entries.append(_entry(rel_path))

    for f in package_files:
        entries.append(_entry(f))

    output = ''
    for e in entries:
        output += ",".join(e) + "\n"

    return output


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
