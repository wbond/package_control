import sublime_plugin

from ..package_creator import PackageCreator


class CreatePackageCommand(sublime_plugin.WindowCommand):

    """
    Command to create a regular .sublime-package file
    """

    def run(self):
        PackageCreator(self.window).show_panel()
