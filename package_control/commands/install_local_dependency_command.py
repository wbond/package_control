import sublime
import sublime_plugin

from .. import text, loader
from ..show_quick_panel import show_quick_panel
from ..package_manager import PackageManager


class InstallLocalDependencyCommand(sublime_plugin.WindowCommand):

    """
    A command that allows package developers to install a dependency that exists
    in the Packages/ folder, but is not currently being loaded.
    """

    def run(self):
        self.manager = PackageManager()
        dependencies = self.manager.list_unloaded_dependencies()
        self.dependency_list = sorted(dependencies, key=lambda s: s.lower())
        if not self.dependency_list:
            sublime.message_dialog(text.format(
                u'''
                Package Control

                All local dependencies are currently loaded
                '''
            ))
            return
        show_quick_panel(self.window, self.dependency_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - addds a loader for the selected
        dependency

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        dependency = self.dependency_list[picked]

        priority, code = self.manager.get_dependency_priority_code(dependency)
        loader.add(priority, dependency, code)

        sublime.status_message(text.format(
            '''
            Dependency %s successfully added to dependency loader -
            restarting Sublime Text may be required
            ''',
            dependency
        ))
