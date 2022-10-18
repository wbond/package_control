import re

import sublime
import sublime_plugin

from ..settings import pc_settings_filename
from ..show_error import show_error


class AddRepositoryCommand(sublime_plugin.ApplicationCommand):

    """
    A command to add a new repository to the user's Package Control settings
    """

    def run(self):
        sublime.active_window().show_input_panel(
            'GitHub, GitLab or BitBucket Web URL, or Custom JSON Repository URL',
            '',
            self.on_done,
            self.on_change,
            self.on_cancel
        )

    def on_done(self, input_text):
        """
        Input panel handler - adds the provided URL as a repository

        :param input_text:
            A string of the URL to the new repository
        """

        input_text = input_text.strip()

        if re.match(r'https?://', input_text, re.I) is None:
            show_error(
                '''
                Unable to add the repository "%s" since it does not appear to
                be served via HTTP (http:// or https://).
                ''',
                input_text
            )
            return

        settings = sublime.load_settings(pc_settings_filename())
        repositories = settings.get('repositories', [])
        if not repositories:
            repositories = []
        repositories.append(input_text)
        settings.set('repositories', repositories)
        sublime.save_settings(pc_settings_filename())
        sublime.status_message('Repository %s successfully added' % input_text)

    def on_change(self, input_text):
        pass

    def on_cancel(self):
        pass
