# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import urlopen


def run(version=None, arch=None):
    """
    Installs a version of Python on Windows

    :return:
        A bool - if Python was installed successfully
    """

    if sys.platform != 'win32':
        raise ValueError('python-install is only designed for Windows')

    if version not in set(['2.6', '3.3']):
        raise ValueError('Invalid version: %r' % version)

    if arch not in set(['x86', 'x64']):
        raise ValueError('Invalid arch: %r' % arch)

    if version == '2.6':
        if arch == 'x64':
            url = 'https://www.python.org/ftp/python/2.6.6/python-2.6.6.amd64.msi'
        else:
            url = 'https://www.python.org/ftp/python/2.6.6/python-2.6.6.msi'
    else:
        if arch == 'x64':
            url = 'https://www.python.org/ftp/python/3.3.5/python-3.3.5.amd64.msi'
        else:
            url = 'https://www.python.org/ftp/python/3.3.5/python-3.3.5.msi'

    home = os.environ.get('USERPROFILE')
    msi_filename = os.path.basename(urlparse(url).path)
    msi_path = os.path.join(home, msi_filename)
    install_path = os.path.join(os.environ.get('LOCALAPPDATA'), 'Python%s-%s' % (version, arch))

    if os.path.exists(os.path.join(install_path, 'python.exe')):
        print(install_path)
        return True

    try:
        with urlopen(url) as r, open(msi_path, 'wb') as f:
            shutil.copyfileobj(r, f)

        proc = subprocess.Popen(
            'msiexec /passive /a %s TARGETDIR=%s' % (msi_filename, install_path),
            shell=True,
            cwd=home
        )
        proc.communicate()

    finally:
        if os.path.exists(msi_path):
            os.unlink(msi_path)

    print(install_path)
    return True


if __name__ == "__main__":
    result = run(sys.argv[1], sys.argv[2])
    sys.exit(int(not result))
