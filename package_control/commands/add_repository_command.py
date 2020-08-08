import re

import sublime
import sublime_plugin

from ..show_error import show_error
from ..settings import pc_settings_filename


class AddRepositoryCommand(sublime_plugin.WindowCommand):

    """
    A command to add a new repository to the user's Package Control settings
    """

    def run(self):
        self.window.show_input_panel(
            'GitHub, GitLab or BitBucket Web URL, or Custom JSON Repository URL',
            '',
            self.on_done,
            self.on_change,
            self.on_cancel
        )

    def on_done(self, input):
        """
        Input panel handler - adds the provided URL as a repository

        :param input:
            A string of the URL to the new repository
        """

        input = input.strip()

        if re.match('https?://', input, re.I) is None:
            show_error(
                u'''
                Unable to add the repository "%s" since it does not appear to
                be served via HTTP (http:// or https://).
                ''',
                input
            )
            return

        settings = sublime.load_settings(pc_settings_filename())
        repositories = settings.get('repositories', [])
        if not repositories:
            repositories = []
        repositories.append(input)
        settings.set('repositories', repositories)
        sublime.save_settings(pc_settings_filename())
        sublime.status_message('Repository %s successfully added' % input)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass
