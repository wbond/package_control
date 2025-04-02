import asyncio
import os

from ..cache import set_cache, get_cache
from ..show_error import show_error
from ..processes import list_process_names
from .vcs_upgrader import VcsUpgrader


class GitUpgrader(VcsUpgrader):

    """
    Allows upgrading a local git-repository-based package
    """

    cli_name = 'git'

    def __init__(self, *args):
        super(GitUpgrader, self).__init__(*args)

        name = 'git'
        if os.name == 'nt':
            name += '.exe'

        self.binary = self.find_binary(name)
        if not self.binary:
            show_error(
                '''
                Unable to find %s.

                Please set the "git_binary" setting by accessing the
                Preferences > Package Settings > Package Control > Settings
                \u2013 User menu entry.

                The Settings \u2013 Default entry can be used for reference,
                but changes to that will be overwritten upon next upgrade.
                ''',
                name
            )

        if os.name == 'nt' and 'GIT_SSH' not in os.environ:
            tortoise_plink = self.find_binary('TortoisePlink.exe')
            if tortoise_plink and 'pageant.exe' in list_process_names():
                os.environ.setdefault('GIT_SSH', tortoise_plink)

    async def get_working_copy_info(self):
        # Get the current branch name
        res = await self.execute(
            args=[self.binary, 'symbolic-ref', '-q', 'HEAD'],
            cwd=self.working_copy
        )
        # Handle the detached head state
        if not res:
            return False
        branch = res.replace('refs/heads/', '')

        # Figure out the remote and the branch name on the remote
        remote, res = await asyncio.gather(
            self.execute(
                [self.binary, 'config', '--get', 'branch.{}.remote'.format(branch)],
                self.working_copy,
                ignore_errors='.*'
            ),
            self.execute(
                [self.binary, 'config', '--get', 'branch.{}.merge'.format(branch)],
                self.working_copy,
                ignore_errors='.*'
            )
        )
        if not remote or not res:
            return False

        remote_branch = res.replace('refs/heads/', '')

        return {
            'branch': branch,
            'remote': remote,
            'remote_branch': remote_branch
        }

    async def run(self):
        """
        Updates the repository with remote changes

        :return: False or error, or True on success
        """

        info = await self.get_working_copy_info()
        if info is False:
            return False

        result = await self.execute(
            args=[self.binary, *self.update_command, info['remote'], info['remote_branch']],
            cwd=self.working_copy,
            meaningful_output=True
        )
        if result is not False:
            cache_key = self.working_copy + '.incoming'
            set_cache(cache_key, None, 0)

        return True

    async def incoming(self):
        """:return: bool if remote revisions are available"""

        cache_key = self.working_copy + '.incoming'
        incoming = get_cache(cache_key)
        if incoming is not None:
            return incoming

        info = await self.get_working_copy_info()
        if info is False:
            return False

        res = await self.execute(
            args=[self.binary, 'fetch', info['remote']],
            cwd=self.working_copy
        )
        if res is False:
            return False

        output = await self.execute(
            args=[self.binary, 'log', '..{}/{}'.format(info['remote'], info['remote_branch'])],
            cwd=self.working_copy,
            meaningful_output=True
        )
        if output is False:
            return False

        incoming = len(output) > 0

        set_cache(cache_key, incoming, self.cache_length)
        return incoming

    async def latest_commit(self):
        """
        :return:
            The latest commit hash
        """

        output = await self.execute(
            args=[self.binary, 'rev-parse', '--short', 'HEAD'],
            cwd=self.working_copy
        )
        if output is False:
            return False

        return output.strip()
