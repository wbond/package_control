import os

from ..cache import set_cache, get_cache
from ..show_error import show_error
from .vcs_upgrader import VcsUpgrader


class HgUpgrader(VcsUpgrader):

    """
    Allows upgrading a local mercurial-repository-based package
    """

    cli_name = 'hg'

    ok_returncodes = set([0, 1])

    def __init__(self, *args):
        super(HgUpgrader, self).__init__(*args)

        name = 'hg'
        if os.name == 'nt':
            name += '.exe'
        self.binary = self.find_binary(name)
        if not self.binary:
            show_error(
                '''
                Unable to find %s.

                Please set the "hg_binary" setting by accessing the
                Preferences > Package Settings > Package Control > Settings
                \u2013 User menu entry.

                The Settings \u2013 Default entry can be used for reference,
                but changes to that will be overwritten upon next upgrade.
                ''',
                name
            )

    async def run(self):
        """
        Updates the repository with remote changes

        :return: False or error, or True on success
        """
        result = await self.execute(
            args=[self.binary, *self.update_command, 'default'],
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

        output = await self.execute(
            args=[self.binary, 'in', '-q', 'default'],
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
            args=[self.binary, 'id', '-i'],
            cwd=self.working_copy
        )
        if output is False:
            return False

        return output.strip()
