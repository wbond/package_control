import zipfile
import os
import hashlib
import json
from os import path
try:
    from urlparse import urlparse
    str_cls = unicode  # noqa
    from cStringIO import StringIO as BytesIO
    package_control_dir = os.getcwd()
except (ImportError) as e:
    from urllib.parse import urlparse
    str_cls = str
    from io import BytesIO
    package_control_dir = path.dirname(path.dirname(__file__))

import sublime

from .clear_directory import clear_directory
from .download_manager import downloader
from .downloaders.downloader_exception import DownloaderException
from .console_write import console_write
from . import loader, sys_path
from .open_compat import open_compat, read_compat
from .semver import SemVer
from .file_not_found_error import FileNotFoundError
from .settings import pc_settings_filename


def mark_bootstrapped():
    """
    Mark Package Control as successfully bootstrapped
    """

    pc_settings = sublime.load_settings(pc_settings_filename())

    if not pc_settings.get('bootstrapped'):
        pc_settings.set('bootstrapped', True)
        sublime.save_settings(pc_settings_filename())


def bootstrap_dependency(settings, url, hash_, priority, version, on_complete):
    """
    Downloads a dependency from a hard-coded URL - only used for bootstrapping _ssl
    on Linux and ST2/Windows

    :param settings:
        Package Control settings

    :param url:
        The non-secure URL to download from

    :param hash_:
        The sha256 hash of the package file

    :param version:
        The version number of the package

    :param priority:
        A three-digit number that controls what order packages are
        injected in

    :param on_complete:
        A callback to be run in the main Sublime thread, so it can use the API
    """

    package_filename = path.basename(urlparse(url).path)
    package_basename, _ = path.splitext(package_filename)

    package_dir = path.join(sys_path.packages_path, package_basename)

    version = SemVer(version)

    # The package has already been installed. Don't reinstall unless we have
    # a newer version.
    if path.exists(package_dir) and loader.exists(package_basename):
        try:
            dep_metadata_path = path.join(package_dir, 'dependency-metadata.json')
            with open_compat(dep_metadata_path, 'r') as f:
                metadata = json.loads(read_compat(f))
            old_version = SemVer(metadata['version'])
            if version <= old_version:
                sublime.set_timeout(mark_bootstrapped, 10)
                return

            console_write(
                u'''
                Upgrading bootstrapped dependency %s to %s from %s
                ''',
                (package_basename, version, old_version)
            )

        except (KeyError, FileNotFoundError):
            # If we can't determine the old version, install the new one
            pass

    with downloader(url, settings) as manager:
        try:
            console_write(
                u'''
                Downloading bootstrapped dependency %s
                ''',
                package_basename
            )
            data = manager.fetch(url, 'Error downloading bootstrapped dependency %s.' % package_basename)
            console_write(
                u'''
                Successfully downloaded bootstraped dependency %s
                ''',
                package_basename
            )
            data_io = BytesIO(data)

        except (DownloaderException) as e:
            console_write(e)
            return

    data_hash = hashlib.sha256(data).hexdigest()
    if data_hash != hash_:
        console_write(
            u'''
            Error validating bootstrapped dependency %s (got %s instead of %s)
            ''',
            (package_basename, data_hash, hash_)
        )
        return

    try:
        data_zip = zipfile.ZipFile(data_io, 'r')
    except (zipfile.BadZipfile):
        console_write(
            u'''
            Error unzipping bootstrapped dependency %s
            ''',
            package_filename
        )
        return

    if not path.exists(package_dir):
        os.makedirs(package_dir, 0o755)
    else:
        clear_directory(package_dir)

    code = None
    for zip_path in data_zip.namelist():
        dest = zip_path

        if not isinstance(dest, str_cls):
            dest = dest.decode('utf-8', 'strict')

        dest = dest.replace('\\', '/')

        # loader.py is included for backwards compatibility. New code should use
        # loader.code with Python inside of it. We no longer use loader.py since
        # we can't have any files ending in .py in the root of a package,
        # otherwise Sublime Text loads it as a plugin and then the dependency
        # path added to sys.path and the package path loaded by Sublime Text
        # conflict and there will be errors when Sublime Text tries to
        # initialize plugins. By using loader.code, developers can git clone a
        # dependency into their Packages folder without issue.
        if dest in set([u'loader.py', u'loader.code']):
            code = data_zip.read(zip_path).decode('utf-8')
            if dest == u'loader.py':
                continue

        dest = path.join(package_dir, dest)

        if dest[-1] == '/':
            if not path.exists(dest):
                os.makedirs(dest, 0o755)
        else:
            dest_dir = path.dirname(dest)
            if not path.exists(dest_dir):
                os.makedirs(dest_dir, 0o755)

            with open(dest, 'wb') as f:
                f.write(data_zip.read(zip_path))

    data_zip.close()

    loader.add_or_update(priority, package_basename, code)

    console_write(
        u'''
        Successfully installed bootstrapped dependency %s
        ''',
        package_basename
    )

    sublime.set_timeout(mark_bootstrapped, 10)
    if on_complete:
        sublime.set_timeout(on_complete, 100)
