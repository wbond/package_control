import os

from ..cache import set_cache, get_cache
from ..show_error import show_error
from .vcs_upgrader import VcsUpgrader


class GitUpgrader(VcsUpgrader):
    """
    Allows upgrading a local git-repository-based package
    """

    cli_name = 'git'

    def retrieve_binary(self):
        """
        Returns the path to the git executable

        :return: The string path to the executable or False on error
        """

        name = 'git'
        if os.name == 'nt':
            name += '.exe'
        binary = self.find_binary(name)
        if binary and os.path.isdir(binary):
            full_path = os.path.join(binary, name)
            if os.path.exists(full_path):
                binary = full_path
        if not binary:
            show_error((u'Unable to find %s. Please set the git_binary setting by accessing the ' +
                u'Preferences > Package Settings > Package Control > Settings \u2013 User menu entry. ' +
                u'The Settings \u2013 Default entry can be used for reference, but changes to that will be ' +
                u'overwritten upon next upgrade.') % name)
            return False

        if os.name == 'nt':
            tortoise_plink = self.find_binary('TortoisePlink.exe')
            if tortoise_plink:
                os.environ.setdefault('GIT_SSH', tortoise_plink)
        return binary

    def run(self):
        """
        Updates the repository with remote changes

        :return: False or error, or True on success
        """

        binary = self.retrieve_binary()
        if not binary:
            return False
        args = [binary]
        args.extend(self.update_command)
        self.execute(args, self.working_copy)
        return True

    def incoming(self):
        """:return: bool if remote revisions are available"""

        cache_key = self.working_copy + '.incoming'
        incoming = get_cache(cache_key)
        if incoming != None:
            return incoming

        binary = self.retrieve_binary()
        if not binary:
            return False

        res = self.execute([binary, 'fetch'], self.working_copy)
        if res == False:
            return False

        args = [binary, 'log']
        args.append('..' + '/'.join(self.update_command[-2:]))
        output = self.execute(args, self.working_copy)
        incoming = len(output) > 0

        set_cache(cache_key, incoming, self.cache_length)
        return incoming
