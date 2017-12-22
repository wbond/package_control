import re

import sublime
import sublime_plugin

from ..settings import load_list_setting
from ..settings import pc_settings_filename
from ..show_error import show_error


class AddRepositoryCommand(sublime_plugin.WindowCommand):

    """
    A command to add a new repository to the user's Package Control settings
    """

    def run(self):
        self.window.show_input_panel(
            'GitHub or BitBucket Web URL, or Custom JSON Repository URL',
            '',
            self.on_done,
            None,
            None
        )

    def on_done(self, text):
        """
        Input panel handler - adds the provided URL as a repository

        :param text:
            A string of the URL to the new repository
        """

        text = text.strip()

        if re.match('https?://', text, re.I) is None:
            show_error(
                '''
                Unable to add the repository "%s" since it does not appear to
                be served via HTTP (http:// or https://).
                ''',
                text
            )
            return

        settings = sublime.load_settings(pc_settings_filename())
        repositories = load_list_setting(settings, 'repositories')
        repositories.append(text)
        settings.set('repositories', repositories)
        sublime.save_settings(pc_settings_filename())
        sublime.status_message('Repository %s successfully added' % text)
