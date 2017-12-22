import sublime
import sublime_plugin

from .. import loader
from .. import text
from ..package_manager import PackageManager
from ..show_quick_panel import show_quick_panel


class InstallLocalDependencyCommand(sublime_plugin.WindowCommand):

    """
    A command that allows package developers to install a dependency that exists
    in the Packages/ folder, but is not currently being loaded.
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        self.manager = PackageManager()
        self.dependency_list = None

    def run(self):
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
