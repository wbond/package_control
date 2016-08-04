import os
import subprocess
import re
import sys

from .console_write import console_write
from .unicode import unicode_from_os
from .show_error import show_error
from . import text

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

try:
    # Allow using this file on the website where the sublime
    # module is unavailable
    import sublime
except (ImportError):
    sublime = None

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
            if re.search('^[a-zA-Z0-9/_^\\-\\.:=]+$', arg) is None:
                arg = u"'" + arg.replace(u"'", u"'\\''") + u"'"
            escaped_args.append(arg)
        return u' '.join(escaped_args)


class Cli(object):

    """
    Base class for running command line apps

    :param binary_locations:
        The full filesystem path to the executable for the version control
        system. May be set to None to allow the code to try and find it. May
        also be a list of locations to attempt. This allows settings to be
        shared across operating systems.
    """

    # Prevent duplicate lookups
    binary_paths = {}

    cli_name = None

    ok_returncodes = set([0])

    def __init__(self, binary_locations, debug):
        self.binary_locations = binary_locations
        self.debug = debug

    def execute(self, args, cwd, input=None, encoding='utf-8', meaningful_output=False, ignore_errors=None):
        """
        Creates a subprocess with the executable/args

        :param args:
            A list of the executable path and all arguments to it

        :param cwd:
            The directory in which to run the executable

        :param input:
            The input text to send to the program

        :param meaningful_output:
            If the output from the command is possibly meaningful and should
            be displayed if in debug mode

        :param ignore_errors:
            A regex of errors to ignore

        :return:
            A string of the executable output or False on error
        """

        orig_cwd = cwd

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # Make sure the cwd is ascii
            try:
                cwd.encode('mbcs')
            except UnicodeEncodeError:
                buf = create_unicode_buffer(512)
                if windll.kernel32.GetShortPathNameW(cwd, buf, len(buf)):
                    cwd = buf.value

        if self.debug:
            console_write(
                u'''
                Executing %s [%s]
                ''',
                (create_cmd(args), cwd)
            )

        try:
            if sys.platform == 'win32' and sys.version_info < (3,):
                cwd = cwd.encode('mbcs')
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                cwd=cwd,
                env=os.environ
            )

            if input and isinstance(input, str_cls):
                input = input.encode(encoding)

            stuck = True

            binary_name = os.path.basename(args[0])
            if re.search('git', binary_name):
                is_vcs = True
            elif re.search('hg', binary_name):
                is_vcs = True

            if sublime:
                def kill_proc():
                    if not stuck:
                        return
                    # This doesn't actually work!
                    proc.kill()

                    message = text.format(
                        u'''
                        The process %s seems to have gotten stuck.

                        Command: %s

                        Working directory: %s
                        ''',
                        (binary_name, create_cmd(args), orig_cwd)
                    )
                    if is_vcs:
                        message += text.format(
                            u'''

                            This is likely due to a password or passphrase
                            prompt. Please ensure %s works without a prompt, or
                            change the "ignore_vcs_packages" Package Control
                            setting to true.

                            Sublime Text will need to be restarted once these
                            changes are made.
                            ''',
                            binary_name
                        )
                    show_error(message)
                sublime.set_timeout(kill_proc, 60000)

            output, _ = proc.communicate(input)

            stuck = False

            output = output.decode(encoding)
            output = output.replace('\r\n', '\n').rstrip(' \n\r')

            if proc.returncode not in self.ok_returncodes:
                if not ignore_errors or re.search(ignore_errors, output) is None:
                    message = text.format(
                        u'''
                        Error executing: %s

                        Working directory: %s

                        %s
                        ''',
                        (create_cmd(args), orig_cwd, output)
                    )
                    if is_vcs:
                        message += text.format(
                            '''

                            VCS-based packages can be ignored by changing the
                            "ignore_vcs_packages" setting to true.

                            Sublime Text will need to be restarted once the
                            setting is changed.
                            '''
                        )
                    show_error(message)
                    return False

            if meaningful_output and self.debug and len(output) > 0:
                console_write(output, indent='  ', prefix=False)

            return output

        except (OSError) as e:
            show_error(
                u'''
                Error executing: %s

                %s

                Try checking your "%s_binary" setting?
                ''',
                (create_cmd(args), unicode_from_os(e), self.cli_name)
            )
            return False

    def find_binary(self, name):
        """
        Locates the executable by looking in the PATH and well-known directories

        :param name:
            The string filename of the executable

        :return:
            The filesystem path to the executable, or None if not found
        """

        # Use the cached path
        if self.cli_name in Cli.binary_paths:
            return Cli.binary_paths[self.cli_name]

        check_binaries = []

        # Use the settings first
        if self.binary_locations:
            if not isinstance(self.binary_locations, list):
                self.binary_locations = [self.binary_locations]
            check_binaries.extend(self.binary_locations)

        # Next check the PATH
        for dir_ in os.environ['PATH'].split(os.pathsep):
            check_binaries.append(os.path.join(dir_, name))

        # Finally look in common locations that may not be in the PATH
        if os.name == 'nt':
            dirs = [
                'C:\\Program Files\\Git\\bin',
                'C:\\Program Files (x86)\\Git\\bin',
                'C:\\Program Files\\TortoiseGit\\bin',
                'C:\\Program Files\\Mercurial',
                'C:\\Program Files (x86)\\Mercurial',
                'C:\\Program Files (x86)\\TortoiseHg',
                'C:\\Program Files\\TortoiseHg',
                'C:\\cygwin\\bin'
            ]
        else:
            # ST seems to launch with a minimal set of environmental variables
            # on OS X, so we add some common paths for it
            dirs = ['/usr/local/git/bin', '/usr/local/bin']

        for dir_ in dirs:
            check_binaries.append(os.path.join(dir_, name))

        if self.debug:
            console_write(
                u'''
                Looking for %s at: "%s"
                ''',
                (self.cli_name, '", "'.join(check_binaries))
            )

        for path in check_binaries:
            if os.path.exists(path) and not os.path.isdir(path) and os.access(path, os.X_OK):
                if self.debug:
                    console_write(
                        u'''
                        Found %s at "%s"
                        ''',
                        (self.cli_name, path)
                    )
                Cli.binary_paths[self.cli_name] = path
                return path

        if self.debug:
            console_write(
                u'''
                Could not find %s on your machine
                ''',
                self.cli_name
            )
        return None
