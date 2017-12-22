import sublime
import sublime_plugin

from .. import text
from ..settings import load_list_setting
from ..settings import pc_settings_filename
from ..show_quick_panel import show_quick_panel


class RemoveRepositoryCommand(sublime_plugin.WindowCommand):

    """
    A command to remove a repository from the user's Package Control settings
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        self.settings = None
        self.repositories = None

    def run(self):
        self.settings = sublime.load_settings(pc_settings_filename())
        self.repositories = load_list_setting(self.settings, 'repositories')
        if not self.repositories:
            sublime.message_dialog(text.format(
                '''
                Package Control

                There are no repositories to remove
                '''
            ))
            return

        show_quick_panel(self.window, self.repositories, self.on_done)

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
