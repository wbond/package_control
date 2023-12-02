import sublime_plugin

from ..package_creator import PackageCreator


class CreatePackageCommand(sublime_plugin.ApplicationCommand):

    """
    Command to create a regular .sublime-package file
    """

    def run(self):
        PackageCreator().run()
