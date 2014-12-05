import zipfile
import os
import hashlib
import sys
import json
from os import path
from textwrap import dedent
try:
    from urlparse import urlparse
    str_cls = unicode
    from cStringIO import StringIO as BytesIO
    package_control_dir = os.getcwd()
except (ImportError) as e:
    from urllib.parse import urlparse
    str_cls = str
    from io import BytesIO
    package_control_dir = path.dirname(path.dirname(__file__))

import sublime

from .download_manager import downloader
from .downloaders.downloader_exception import DownloaderException
from .settings import pc_settings_filename, load_list_setting, save_list_setting
from .console_write import console_write
from . import loader
from .sys_path import st_dir



def bootstrap_dependency(settings, url, hash_, priority, on_complete):
    """
    Downloads a dependency from a hard-coded URL - only used for bootstrapping _ssl
    on Linux and ST2/Windows

    :param settings:
        Package Control settings

    :param url:
        The non-secure URL to download from

    :param hash_:
        The sha256 hash of the package file

    :param priority:
        A three-digit number that controls what order packages are
        injected in

    :param on_complete:
        A callback to be run in the main Sublime thread, so it can use the API
    """

    package_filename = path.basename(urlparse(url).path)
    package_basename, _ = path.splitext(package_filename)

    packages_dir = path.join(st_dir, u'Packages')
    if not packages_dir:
        return
    package_dir = path.join(packages_dir, package_basename)

    # The package has already been installed
    if path.exists(package_dir):
        return

    with downloader(url, settings) as manager:
        try:
            console_write(u'Downloading bootstrapped dependency %s' % package_basename, True)
            data = manager.fetch(url, 'Error downloading bootstrapped dependency %s.' % package_basename)
            console_write(u'Successfully downloaded bootstraped dependency %s' % package_basename, True)
            data_io = BytesIO(data)

        except (DownloaderException) as e:
            console_write(u'%s' % str(e), True)
            return

    data_hash = hashlib.sha256(data).hexdigest()
    if data_hash != hash_:
        console_write(u'Error validating bootstrapped dependency %s (got %s instead of %s)' % (package_basename, data_hash, hash_), True)
        return

    try:
        data_zip = zipfile.ZipFile(data_io, 'r')
    except (zipfile.BadZipfile):
        console_write(u'Error unzipping bootstrapped dependency %s' % package_filename, True)
        return

    if not path.exists(package_dir):
        os.mkdir(package_dir, 0o755)

    code = None
    for zip_path in data_zip.namelist():
        dest = zip_path

        if not isinstance(dest, str_cls):
            dest = dest.decode('utf-8', 'strict')

        dest = dest.replace('\\', '/')

        if dest == u'loader.py':
            code = data_zip.read(zip_path).decode('utf-8')
            continue

        dest = path.join(package_dir, dest)

        if dest[-1] == '/':
            if not path.exists(dest):
                os.mkdir(dest, 0o755)
        else:
            dest_dir = path.dirname(dest)
            if not path.exists(dest_dir):
                os.mkdir(dest_dir, 0o755)

            with open(dest, 'wb') as f:
                f.write(data_zip.read(zip_path))

    data_zip.close()

    loader.add(priority, package_basename, code)

    console_write(u'Successfully installed bootstrapped dependency %s' % package_basename, True)

    def add_to_installed_dependencies():
        filename = pc_settings_filename()
        settings = sublime.load_settings(filename)
        old = load_list_setting(settings, 'installed_dependencies')
        new = list(old)
        if loader.loader_package_name not in new:
            new.append(loader_package_name)
        if package_basename not in new:
            new.append(package_basename)
        save_list_setting(settings, filename, 'installed_dependencies', new, old)
    sublime.set_timeout(add_to_installed_dependencies, 10)

    if on_complete:
        # Give add_to_installed_dependencies() time to run
        sublime.set_timeout(on_complete, 200)
