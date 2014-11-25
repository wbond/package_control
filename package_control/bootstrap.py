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


def get_sublime_text_dir(name):
    cur_packages_dir = path.dirname(package_control_dir)

    try:
        if not isinstance(cur_packages_dir, str_cls):
            cur_packages_dir = cur_packages_dir.decode('utf-8', 'strict')
        return path.normpath(path.join(cur_packages_dir, '..', name))

    except (UnicodeDecodeError):
        print(u'Package Control: An error occurred decoding the Package Control path as UTF-8')
        return


def bootstrap_early_package(settings, name, url, hash_, priority, inject_code, on_complete):
    """
    Downloads packages that need to be injected early in the Sublime Text
    load process so that other packages can use them.

    :param settings:
        Package Control settings

    :param name:
        The user-friendly name for status messages

    :param url:
        The non-secure URL to download from

    :param hash_:
        The sha256 hash of the package file

    :param priority:
        A three-digit number that controls what order packages are
        injected in

    :param inject_code:
        The python code to inject the package into sys.path

    :param on_complete:
        A callback to be run in the main Sublime thread, so it can use the API
    """

    package_filename = path.basename(urlparse(url).path)
    package_basename, _ = path.splitext(package_filename)

    packages_dir = get_sublime_text_dir('Packages')
    if not packages_dir:
        return
    package_dir = path.join(packages_dir, package_basename)

    # The package has already been installed
    if path.exists(package_dir):
        return

    with downloader(url, settings) as manager:
        try:
            print(u'Package Control: Downloading %s' % name)
            data = manager.fetch(url, 'Error downloading %s.' % name)
            print(u'Package Control: Successfully downloaded %s' % name)
            data_io = BytesIO(data)

        except (DownloaderException) as e:
            print(u'Package Control: %s' % str(e))
            return

    data_hash = hashlib.sha256(data).hexdigest()
    if data_hash != hash_:
        print(u'Package Control: Error validating %s (got %s instead of %s)' % (name, data_hash, hash_))
        return

    try:
        data_zip = zipfile.ZipFile(data_io, 'r')
    except (zipfile.BadZipfile):
        print(u'Package Control: Error unzipping %s' % package_filename)
        return

    if not path.exists(package_dir):
        os.mkdir(package_dir, 0o755)

    for zip_path in data_zip.namelist():
        dest = zip_path

        if not isinstance(dest, str_cls):
            dest = dest.decode('utf-8', 'strict')

        dest = dest.replace('\\', '/')

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

    inject_code = dedent(inject_code).strip() + '\n'
    filename = '%s-%s-inject.py' % (priority, package_basename)

    loader_name = '0-package_control_loader'

    if sys.version_info < (3,):
        package_dir = path.join(packages_dir, loader_name)

        if not path.exists(package_dir):
            os.mkdir(package_dir, 0o755)

        file_path = path.join(package_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(inject_code.encode('utf-8'))

    else:
        installed_packages_dir = get_sublime_text_dir('Installed Packages')
        if not installed_packages_dir:
            return

        file_path = path.join(installed_packages_dir, '%s.sublime-package' % loader_name)

        mode = 'a' if os.path.exists(file_path) else 'w'
        with zipfile.ZipFile(file_path, mode) as z:
            if mode == 'w':
                metadata = {
                    "version": "1.0.0",
                    "sublime_text": "*",
                    # Tie the loader to the platform so we can detect
                    # people syncing packages incorrectly.
                    "platforms": [sublime.platform()],
                    "url": "https://packagecontrol.io",
                    "description": "Package Control loader for supplemental Python packages"
                }
                z.writestr('package-metadata.json', json.dumps(metadata).encode('utf-8'))
            z.writestr(filename, inject_code.encode('utf-8'))

    print(u'Package Control: Successfully installed %s' % name)

    def add_to_installed_packages():
        filename = pc_settings_filename()
        settings = sublime.load_settings(filename)
        installed_packages = load_list_setting(settings, 'installed_packages')
        new_installed_packages = list(installed_packages)
        if loader_name not in new_installed_packages:
            new_installed_packages.append(loader_name)
        if package_basename not in new_installed_packages:
            new_installed_packages.append(package_basename)
        save_list_setting(settings, filename, 'installed_packages', new_installed_packages, installed_packages)
    sublime.set_timeout(add_to_installed_packages, 10)

    if on_complete:
        # Give add_to_installed_packages() time to run
        sublime.set_timeout(on_complete, 200)
