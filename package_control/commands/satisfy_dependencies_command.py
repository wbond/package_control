import threading

import sublime
import sublime_plugin

from functools import partial

from ..show_error import show_error
from ..package_manager import PackageManager
from ..thread_progress import ThreadProgress


class SatisfyDependenciesCommand(sublime_plugin.WindowCommand):
    """
    A command that finds all dependencies required by the installed packages
    and makes sure they are all installed and up-to-date.
    """

    def run(self):
        manager = PackageManager()
        thread = SatisfyDependenciesThread(manager)
        thread.start()
        ThreadProgress(thread, 'Satisfying dependencies', '')


class SatisfyDependenciesThread(threading.Thread):
    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self, manager):
        self.manager = manager
        threading.Thread.__init__(self)

    def show_error(msg):
        sublime.set_timeout(partial(show_error, msg), 10)

    def run(self):
        required_dependencies = self.manager.find_required_dependencies()

        if not self.manager.install_dependencies(required_dependencies, fail_early=False):
            self.show_error(u'One or more dependencies could not be installed '
                            'or updated. Please check the console for details.')

        if not self.manager.cleanup_dependencies(required_dependencies=required_dependencies):
            self.show_error(u'One or more orphaned dependencies could not be '
                            'removed. Please check the console for details.')
