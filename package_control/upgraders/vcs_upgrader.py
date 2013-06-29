import subprocess
import os

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

from ..console_write import console_write
from ..unicode import unicode_from_os
from ..show_error import show_error
from ..cmd import create_cmd


class VcsUpgrader():
    """
    Base class for updating packages that are a version control repository on local disk

    :param vcs_binary:
        The full filesystem path to the executable for the version control
        system. May be set to None to allow the code to try and find it.

    :param update_command:
        The command to pass to the version control executable to update the
        repository.

    :param working_copy:
        The local path to the working copy/package directory

    :param cache_length:
        The lenth of time to cache if incoming changesets are available
    """

    def __init__(self, vcs_binary, update_command, working_copy, cache_length, debug):
        self.binary = vcs_binary
        self.update_command = update_command
        self.working_copy = working_copy
        self.cache_length = cache_length
        self.debug = debug

    def execute(self, args, cwd):
        """
        Creates a subprocess with the executable/args

        :param args:
            A list of the executable path and all arguments to it

        :param cwd:
            The directory in which to run the executable

        :return: A string of the executable output
        """

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # Make sure the cwd is ascii
            try:
                cwd.encode('ascii')
            except UnicodeEncodeError:
                buf = create_unicode_buffer(512)
                if windll.kernel32.GetShortPathNameW(cwd, buf, len(buf)):
                    cwd = buf.value

        if self.debug:
            console_write(u"Trying to execute command %s" % create_cmd(args), True)

        try:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                startupinfo=startupinfo, cwd=cwd)

            output = proc.stdout.read()
            output = output.decode('utf-8')
            output = output.replace('\r\n', '\n').rstrip(' \n\r')

            return output

        except (OSError) as e:
            cmd = create_cmd(args)
            error = unicode_from_os(e)
            message = u"Error executing: %s\n%s\n\nTry checking your \"%s_binary\" setting?" % (cmd, error, self.vcs_type)
            show_error(message)
            return False

    def find_binary(self, name):
        """
        Locates the executable by looking in the PATH and well-known directories

        :param name:
            The string filename of the executable

        :return: The filesystem path to the executable, or None if not found
        """

        if self.binary:
            if self.debug:
                error_string = u"Using \"%s_binary\" from settings \"%s\"" % (
                    self.vcs_type, self.binary)
                console_write(error_string, True)
            return self.binary

        # Try the path first
        for dir in os.environ['PATH'].split(os.pathsep):
            path = os.path.join(dir, name)
            if os.path.exists(path):
                if self.debug:
                    console_write(u"Found %s at \"%s\"" % (self.vcs_type, path), True)
                return path

        # This is left in for backwards compatibility and for windows
        # users who may have the binary, albeit in a common dir that may
        # not be part of the PATH
        if os.name == 'nt':
            dirs = ['C:\\Program Files\\Git\\bin',
                'C:\\Program Files (x86)\\Git\\bin',
                'C:\\Program Files\\TortoiseGit\\bin',
                'C:\\Program Files\\Mercurial',
                'C:\\Program Files (x86)\\Mercurial',
                'C:\\Program Files (x86)\\TortoiseHg',
                'C:\\Program Files\\TortoiseHg',
                'C:\\cygwin\\bin']
        else:
            dirs = ['/usr/local/git/bin']

        for dir in dirs:
            path = os.path.join(dir, name)
            if os.path.exists(path):
                if self.debug:
                    console_write(u"Found %s at \"%s\"" % (self.vcs_type, path), True)
                return path

        if self.debug:
            console_write(u"Could not find %s on your machine" % self.vcs_type, True)
        return None
