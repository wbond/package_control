import threading

import sublime
import sublime_plugin

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

    def run(self):
        dependencies = self.manager.find_required_dependencies()
        result = self.manager.install_dependencies(dependencies)
        if not result:
            def do_show_error():
                show_error(u'One or more dependencies could not be ' + \
                    'installed or updated. Please check the console for ' + \
                    'details.')
            sublime.set_timeout(do_show_error, 10)
