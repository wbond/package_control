import os
import shutil
import subprocess

from ..cmd import create_cmd
from ..console_write import console_write
from .binary_not_found_error import BinaryNotFoundError
from .non_clean_exit_error import NonCleanExitError


class CliDownloader(object):

    """
    Base for downloaders that use a command line program

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.settings = settings
        self.stderr = b''

    def clean_tmp_file(self):
        if self.tmp_file and os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)

    def find_binary(self, name):
        """
        Finds the given executable name in the system PATH

        :param name:
            The exact name of the executable to find

        :return:
            The absolute path to the executable

        :raises:
            BinaryNotFoundError when the executable can not be found
        """

        dirs = os.environ['PATH']
        if os.name != 'nt':
            # This is mostly for OS X, which seems to launch ST with a
            # minimal set of environmental variables
            dirs += os.pathsep + '/usr/local/bin'

        path = shutil.which(name, path=dirs)
        if not path:
            raise BinaryNotFoundError('The binary %s could not be located' % name)
        return path

    def execute(self, args):
        """
        Runs the executable and args and returns the result

        :param args:
            A list of the executable path and all arguments to be passed to it

        :return:
            The text output of the executable

        :raises:
            NonCleanExitError when the executable exits with an error
        """

        if self.settings.get('debug'):
            console_write(
                '''
                Trying to execute command %s
                ''',
                create_cmd(args)
            )

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )

        output, self.stderr = proc.communicate()
        if proc.returncode != 0:
            error = NonCleanExitError(proc.returncode)
            error.stderr = self.stderr
            error.stdout = output
            raise error
        return output
