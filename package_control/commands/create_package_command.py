import sublime_plugin

from ..package_creator import PackageCreator


class CreatePackageCommand(sublime_plugin.WindowCommand, PackageCreator):
    """
    Command to create a regular .sublime-package file
    """

    def run(self):
        self.show_panel()

    def on_done(self, picked):
        """
        Quick panel user selection handler - processes the user package
        selection and create the package file

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package_name = self.packages[picked]
        package_destination = self.get_package_destination()

        if self.manager.create_package(package_name, package_destination):
            self.window.run_command('open_dir', {"dir":
                package_destination, "file": package_name +
                '.sublime-package'})
