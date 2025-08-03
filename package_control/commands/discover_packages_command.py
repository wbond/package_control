import sublime
import sublime_plugin


class DiscoverPackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that opens the Package Control website
    """

    def run(self):
        sublime.run_command('open_url', {'url': 'https://packages.sublimetext.io'})
