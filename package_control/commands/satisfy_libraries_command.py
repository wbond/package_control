import threading

import sublime_plugin

from ..console_write import console_write
from ..package_manager import PackageManager
from ..show_error import show_error
from ..thread_progress import ThreadProgress


class SatisfyLibrariesCommand(sublime_plugin.WindowCommand):

    """
    A command that finds all libraries required by the installed packages
    and makes sure they are all installed and up-to-date.
    """

    def run(self):
        manager = PackageManager()
        thread = SatisfyLibrariesThread(manager)
        thread.start()
        ThreadProgress(thread, 'Satisfying libraries', '')


class SatisfyLibrariesThread(threading.Thread):

    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self, manager):
        self.manager = manager
        threading.Thread.__init__(self)

    def run(self):
        error = False

        required_libraries = self.manager.find_required_libraries()

        if not self.manager.install_libraries(libraries=required_libraries, fail_early=False):
            show_error(
                '''
                One or more libraries could not be installed or updated.

                Please check the console for details.
                '''
            )
            error = True

        if not self.manager.cleanup_libraries(required_libraries=required_libraries):
            show_error(
                '''
                One or more orphaned libraries could not be removed.

                Please check the console for details.
                '''
            )
            error = True

        if not error:
            console_write('All libraries have been satisfied')
