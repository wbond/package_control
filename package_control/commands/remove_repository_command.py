import sublime
import sublime_plugin

from ..settings import pc_settings_filename
from ..show_error import show_message


class RemoveRepositoryCommand(sublime_plugin.ApplicationCommand):

    """
    A command to remove a repository from the user's Package Control settings

    Example:

    ```py
    sublime.run_command(
        "remove_repository",
        {
            "url": "https://my-server.com/repository.json",
            "unattended": False  # if True, suppress error dialogs
        }
    )
    ```
    """

    def run(self, url=None, unattended=False):
        settings = sublime.load_settings(pc_settings_filename())
        repositories = settings.get('repositories')
        if not repositories:
            if not url or not unattended:
                show_message('There are no repositories to remove')
            return

        if url:
            try:
                repositories.remove(url)
            except (ValueError):
                pass
            else:
                settings.set('repositories', repositories)
                sublime.save_settings(pc_settings_filename())
                sublime.status_message('Repository %s successfully removed' % url)
            return

        def on_done(index):
            if index == -1:
                return

            self.run(repositories[index])

        sublime.active_window().show_quick_panel(
            repositories,
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
