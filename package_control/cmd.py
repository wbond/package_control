import os
import subprocess
import re

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

from .console_write import console_write
from .unicode import unicode_from_os
from .show_error import show_error

try:
    # Python 2
    str_cls = unicode
except (NameError):
    # Python 3
    str_cls = str


def create_cmd(args, basename_binary=False):
    """
    Takes an array of strings to be passed to subprocess.Popen and creates
    a string that can be pasted into a terminal

    :param args:
        The array containing the binary name/path and all arguments

    :param basename_binary:
        If only the basename of the binary should be disabled instead of the full path

    :return:
        The command string
    """

    if basename_binary:
        args[0] = os.path.basename(args[0])

    if os.name == 'nt':
        return subprocess.list2cmdline(args)
    else:
        escaped_args = []
        for arg in args:
            if re.search('^[a-zA-Z0-9/_^\\-\\.:=]+$', arg) == None:
                arg = u"'" + arg.replace(u"'", u"'\\''") + u"'"
            escaped_args.append(arg)
        return u' '.join(escaped_args)


class Cli(object):
    """
    Base class for running command line apps

    :param binary:
        The full filesystem path to the executable for the version control
        system. May be set to None to allow the code to try and find it.
    """

    cli_name = None

    def __init__(self, binary, debug):
        self.binary = binary
        self.debug = debug

    def execute(self, args, cwd, input=None):
        """
        Creates a subprocess with the executable/args

        :param args:
            A list of the executable path and all arguments to it

        :param cwd:
            The directory in which to run the executable

        :param input:
            The input text to send to the program

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

            if input and isinstance(input, str_cls):
                input = input.encode('utf-8')
            output, _ = proc.communicate(input)
            output = output.decode('utf-8')
            output = output.replace('\r\n', '\n').rstrip(' \n\r')

            return output

        except (OSError) as e:
            cmd = create_cmd(args)
            error = unicode_from_os(e)
            message = u"Error executing: %s\n%s\n\nTry checking your \"%s_binary\" setting?" % (cmd, error, self.cli_name)
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
                    self.cli_name, self.binary)
                console_write(error_string, True)
            return self.binary

        # Try the path first
        for dir_ in os.environ['PATH'].split(os.pathsep):
            path = os.path.join(dir_, name)
            if os.path.exists(path):
                if self.debug:
                    console_write(u"Found %s at \"%s\"" % (self.cli_name, path), True)
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
            # ST seems to launch with a minimal set of environmental variables
            # on OS X, so we add some common paths for it
            dirs = ['/usr/local/git/bin', '/usr/local/bin']

        for dir_ in dirs:
            path = os.path.join(dir_, name)
            if os.path.exists(path):
                if self.debug:
                    console_write(u"Found %s at \"%s\"" % (self.cli_name, path), True)
                return path

        if self.debug:
            console_write(u"Could not find %s on your machine" % self.cli_name, True)
        return None
