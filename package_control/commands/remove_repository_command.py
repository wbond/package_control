import sublime
import sublime_plugin

from ..show_error import show_error
from ..settings import pc_settings_filename


class RemoveRepositoryCommand(sublime_plugin.WindowCommand):
    """
    A command to remove a repository from the user's Package Control settings
    """

    def run(self):
        self.settings = sublime.load_settings(pc_settings_filename())
        self.repositories = self.settings.get('repositories')
        if not self.repositories:
            show_error(u'There are no repositories to remove.')
            return

        self.window.show_quick_panel(self.repositories, self.on_done)

    def on_done(self, index):
        """
        Quick panel handler - removes the repository from settings

        :param index:
            The numeric index of the repository in the list of repositories
        """

        # Cancelled
        if index == -1:
            return

        repository = self.repositories[index]

        try:
            self.repositories.remove(repository)
            self.settings.set('repositories', self.repositories)
            sublime.save_settings(pc_settings_filename())
            sublime.status_message('Repository %s successfully removed' % repository)

        except (ValueError):
            pass
