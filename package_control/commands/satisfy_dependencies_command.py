import threading

import sublime_plugin

from ..console_write import console_write
from ..package_manager import PackageManager
from ..show_error import show_error
from ..thread_progress import ThreadProgress


class SatisfyDependenciesCommand(sublime_plugin.WindowCommand):

    """
    A command that finds all dependencies required by the installed packages
    and makes sure they are all installed and up-to-date.
    """

    def run(self):
        thread = SatisfyDependenciesThread()
        thread.start()
        ThreadProgress(thread, 'Satisfying dependencies', '')


class SatisfyDependenciesThread(threading.Thread):

    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self):
        self.manager = PackageManager()
        threading.Thread.__init__(self)

    def run(self):
        required_dependencies = self.manager.find_required_dependencies()
        error = False

        if not self.manager.install_dependencies(required_dependencies, fail_early=False):
            show_error(
                '''
                One or more dependencies could not be installed or updated.

                Please check the console for details.
                '''
            )
            error = True

        if not self.manager.cleanup_dependencies(required_dependencies=required_dependencies):
            show_error(
                '''
                One or more orphaned dependencies could not be removed.

                Please check the console for details.
                '''
            )
            error = True

        if not error:
            console_write('All dependencies have been satisfied')
