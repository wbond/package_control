import os
import subprocess
import re


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
