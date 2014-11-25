from ..cmd import create_cmd, Cli


class VcsUpgrader(Cli):
    """
    Base class for updating packages that are a version control repository on local disk

    :param vcs_binary_paths:
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

    def __init__(self, vcs_binary_paths, update_command, working_copy, cache_length, debug):
        self.update_command = update_command
        self.working_copy = working_copy
        self.cache_length = cache_length
        super(VcsUpgrader, self).__init__(vcs_binary_paths, debug)
