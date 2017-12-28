import threading
import os

import sublime_plugin

from ..path import unpacked_package_path
from ..path import installed_package_parts
from ..show_error import show_message
from ..show_quick_panel import show_quick_panel
from .existing_packages_command import ExistingPackagesCommand


class ListPackagesCommand(sublime_plugin.WindowCommand):

    """
    A command that shows a list of all installed packages in the quick panel
    """

    def run(self):
        ListPackagesThread(self.window).start()


class ListPackagesThread(threading.Thread, ExistingPackagesCommand):

    """
    A thread to prevent the listing of existing packages from freezing the UI
    """

    def __init__(self, window, filter_function=None):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.

        :param filter_function:
            A callable to filter packages for display. This function gets
            called for each package in the list with a three-element list
            as returned by :meth:`ExistingPackagesCommand.make_package_list`:
              0 - package name
              1 - package description
              2 - [action] installed version; package url
            If the function returns a true value, the package is listed,
            otherwise it is discarded. If `None`, no filtering is performed.
        """

        self.window = window
        self.filter_function = filter_function
        self.package_list = None
        ExistingPackagesCommand.__init__(self)
        threading.Thread.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()
        if self.filter_function:
            self.package_list = list(filter(self.filter_function, self.package_list))

        if not self.package_list:
            show_message('There are no packages to list')
            return
        show_quick_panel(self.window, self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - opens the homepage for any
        selected package in the user's browser

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package_name = self.package_list[picked][0]

        package_dir, package_file = unpacked_package_path(package_name), None
        if not os.path.isdir(package_dir):
            package_dir, package_file = installed_package_parts(package_name)
            if not os.path.isfile(os.path.join(package_dir, package_file)):
                package_file = None

        open_dir_file = {'dir': package_dir}
        if package_file is not None:
            open_dir_file['file'] = package_file

        self.window.run_command('open_dir', open_dir_file)
