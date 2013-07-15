import threading

import sublime
import sublime_plugin

from ..show_error import show_error
from .existing_packages_command import ExistingPackagesCommand
from ..preferences_filename import preferences_filename
from ..thread_progress import ThreadProgress


class RemovePackageCommand(sublime_plugin.WindowCommand,
        ExistingPackagesCommand):
    """
    A command that presents a list of installed packages, allowing the user to
    select one to remove
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        self.window = window
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list('remove')
        if not self.package_list:
            show_error('There are no packages that can be removed.')
            return
        self.window.show_quick_panel(self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - deletes the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.package_list[picked][0]

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            ignored = []

        # Don't disable Package Control so it does not get stuck disabled
        if package != 'Package Control':
            if not package in ignored:
                ignored.append(package)
                settings.set('ignored_packages', ignored)
                sublime.save_settings(preferences_filename())
            ignored.remove(package)

        thread = RemovePackageThread(self.manager, package,
            ignored)
        thread.start()
        ThreadProgress(thread, 'Removing package %s' % package,
            'Package %s successfully removed' % package)


class RemovePackageThread(threading.Thread):
    """
    A thread to run the remove package operation in so that the Sublime Text
    UI does not become frozen
    """

    def __init__(self, manager, package, ignored):
        self.manager = manager
        self.package = package
        self.ignored = ignored
        threading.Thread.__init__(self)

    def run(self):
        self.result = self.manager.remove_package(self.package)

        def unignore_package():
            settings = sublime.load_settings(preferences_filename())
            settings.set('ignored_packages', self.ignored)
            sublime.save_settings(preferences_filename())
        sublime.set_timeout(unignore_package, 10)
