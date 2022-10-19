import re

import sublime
import sublime_plugin

from ..console_write import console_write
from ..settings import pc_settings_filename
from ..show_error import show_error


class AddRepositoryCommand(sublime_plugin.ApplicationCommand):

    """
    A command to add a new repository to the user's Package Control settings

    Example:

    ```py
    sublime.run_command(
        "add_repository",
        {
            "url": "https://my-server.com/repository.json",
            "unattended": False  # don't suppress error dialogs
        }
    )
    ```
    """

    def run(self, url=None, unattended=False):
        if isinstance(url, str):
            url = url.strip()

            if re.match(r'https?://', url, re.I) is None:
                output_fn = console_write if unattended else show_error
                output_fn(
                    '''
                    Unable to add the repository "%s" since it does not appear to
                    be served via HTTP (http:// or https://).
                    ''',
                    url
                )
                return

            settings = sublime.load_settings(pc_settings_filename())
            repositories = settings.get('repositories')
            if not repositories:
                repositories = []
            elif url in repositories:
                return
            repositories.append(url)
            settings.set('repositories', repositories)
            sublime.save_settings(pc_settings_filename())
            sublime.status_message('Repository %s successfully added' % url)
            return

        sublime.active_window().show_input_panel(
            'GitHub, GitLab or BitBucket Web URL, or Custom JSON Repository URL',
            '',
            self.run,
            None,
            None
        )
