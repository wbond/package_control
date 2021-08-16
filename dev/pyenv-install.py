# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import subprocess
import sys


def run(version=None):
    """
    Installs a version of Python on Mac using pyenv

    :return:
        A bool - if Python was installed successfully
    """

    if sys.platform == 'win32':
        raise ValueError('pyenv-install is not designed for Windows')

    if version not in set(['3.3']):
        raise ValueError('Invalid version: %r' % version)

    python_path = os.path.expanduser('~/.pyenv/versions/%s/bin' % version)
    if os.path.exists(os.path.join(python_path, 'python')):
        print(python_path)
        return True

    stdout = ""
    stderr = ""

    proc = subprocess.Popen(
        'command -v pyenv',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    proc.communicate()
    if proc.returncode != 0:
        proc = subprocess.Popen(
            ['brew', 'install', 'pyenv'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        so, se = proc.communicate()
        stdout += so.decode('utf-8')
        stderr += se.decode('utf-8')
        if proc.returncode != 0:
            print(stdout)
            print(stderr, file=sys.stderr)
            return False

    pyenv_script = './%s' % version
    try:
        with open(pyenv_script, 'wb') as f:
            if version == '3.3':
                contents = '#require_gcc\n' \
                    'install_package "openssl-1.0.2k" "https://www.openssl.org/source/old/1.0.2/openssl-1.0.2k.tar.gz' \
                    '#6b3977c61f2aedf0f96367dcfb5c6e578cf37e7b8d913b4ecb6643c3cb88d8c0" mac_openssl\n' \
                    'install_package "readline-8.0" "https://ftpmirror.gnu.org/readline/readline-8.0.tar.gz' \
                    '#e339f51971478d369f8a053a330a190781acb9864cf4c541060f12078948e461" mac_readline' \
                    ' --if has_broken_mac_readline\n' \
                    'install_package "Python-3.3.7" "https://www.python.org/ftp/python/3.3.7/Python-3.3.7.tar.xz' \
                    '#85f60c327501c36bc18c33370c14d472801e6af2f901dafbba056f61685429fe" standard verify_py33'
            f.write(contents.encode('utf-8'))

        args = ['pyenv', 'install', pyenv_script]
        stdin = None
        stdin_contents = None
        env = os.environ.copy()

        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin,
            env=env
        )
        so, se = proc.communicate(stdin_contents)
        stdout += so.decode('utf-8')
        stderr += se.decode('utf-8')

        if proc.returncode != 0:
            print(stdout)
            print(stderr, file=sys.stderr)
            return False

    finally:
        if os.path.exists(pyenv_script):
            os.unlink(pyenv_script)

    print(python_path)
    return True


if __name__ == "__main__":
    result = run(sys.argv[1])
    sys.exit(int(not result))