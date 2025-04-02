import sublime_aio

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_manager import PackageManager
from ..show_error import show_error


class SatisfyLibrariesCommand(sublime_aio.ApplicationCommand):

    """
    A command that finds all libraries required by the installed packages
    and makes sure they are all installed and up-to-date.
    """

    async def run(self):
        manager = PackageManager()

        with ActivityIndicator('Satisfying libraries...') as progress:
            error = False

            required_libraries = manager.find_required_libraries()

            if not await manager.cleanup_libraries(required_libraries=required_libraries):
                show_error(
                    '''
                    One or more orphaned libraries could not be removed.

                    Please check the console for details.
                    '''
                )
                error = True

            if not await manager.install_libraries(libraries=required_libraries, fail_early=False):
                show_error(
                    '''
                    One or more libraries could not be installed or updated.

                    Please check the console for details.
                    '''
                )
                error = True

            if not error:
                message = 'All libraries have been satisfied!'
                console_write(message)
                progress.finish(message)
