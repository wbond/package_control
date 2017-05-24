import textwrap
import threading
import os

import sublime
import sublime_plugin

from .. import text
from ..show_quick_panel import show_quick_panel
from ..package_manager import PackageManager
from .existing_packages_command import ExistingPackagesCommand


# print( "Reloading `Package Control\package_control\commands\list_packages_command.py`" )

class ListPackagesCommand(sublime_plugin.WindowCommand):

    """
    A command that shows a list of all installed packages in the quick panel
    """

    def run(self):
        ListPackagesThread(self.window).start()


class ListPackagesOnViewCommand(sublime_plugin.WindowCommand):

    """
    A command that shows a list of all installed packages in a new view
    """

    def run(self):
        ListPackagesThread(self.window, on_view=True).start()


class ListPackagesThread(threading.Thread, ExistingPackagesCommand):

    """
    A thread to prevent the listing of existing packages from freezing the UI
    """

    def __init__(self, window, filter_function=None, on_view=False):
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
        self.on_view = on_view
        self.filter_function = filter_function
        self.manager = PackageManager()
        threading.Thread.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()
        if self.filter_function:
            self.package_list = list(filter(self.filter_function, self.package_list))

        def show_no_packages():
            sublime.message_dialog(text.format(
                u'''
                Package Control

                There are no packages to list
                '''
            ))

        def show_panel():
            if not self.package_list:
                show_no_packages()
                return
            show_quick_panel(self.window, self.package_list, self.on_done)

        def show_view():
            if not self.package_list:
                show_no_packages()
                return

            new_view = sublime.active_window().new_file()
            package_count = 0
            prefix_indent = "     "
            package_string = ""

            new_view.set_scratch(True)
            new_view.set_name("Packages List")
            new_view.set_syntax_file("Packages/Text/Plain text.tmLanguage")
            new_view.settings().set('tab_size', 8)

            for package in self.package_list:
                package_count += 1;
                wrapper = textwrap.TextWrapper(initial_indent=prefix_indent, width=80, subsequent_indent=prefix_indent)
                package_string += "%3d: <%s>\n" % ( package_count, package[0] )
                package_string += wrapper.fill(package[1]) + "\n" + prefix_indent + "[" + package[2] + "]\n\n"

            # https://forum.sublimetext.com/t/how-to-insert-text-on-view-with-no-indentation/28496
            new_view.run_command("append", {"characters": "Packages list within %d entries:\n\n" % (len(self.package_list))})
            new_view.run_command("append", {"characters": package_string})

            new_view.sel().clear()
            initial_region = sublime.Region(0,0)
            new_view.sel().add(initial_region)
            new_view.show_at_center(initial_region)

        if self.on_view:
            sublime.set_timeout(show_view, 10)
        else:
            sublime.set_timeout(show_panel, 10)

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

        def open_dir():
            package_dir = self.manager.get_package_dir(package_name)
            package_file = None
            if not os.path.exists(package_dir):
                package_dir = self.manager.settings['installed_packages_path']
                package_file = package_name + '.sublime-package'
                if not os.path.exists(os.path.join(package_dir, package_file)):
                    package_file = None

            open_dir_file = {'dir': package_dir}
            if package_file is not None:
                open_dir_file['file'] = package_file

            self.window.run_command('open_dir', open_dir_file)
        sublime.set_timeout(open_dir, 10)

