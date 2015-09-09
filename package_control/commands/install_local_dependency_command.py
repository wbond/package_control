import sublime
import sublime_plugin

import os

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

        dependency_path = self.manager.get_package_dir(dependency)
        hidden_file_path = os.path.join(dependency_path, '.sublime-dependency')
        loader_py_path = os.path.join(dependency_path, 'loader.py')
        loader_code_path = os.path.join(dependency_path, 'loader.code')

        priority = None

        # Look in the .sublime-dependency file to see where in the dependency
        # load order this dependency should be installed
        if os.path.exists(hidden_file_path):
            with open(hidden_file_path, 'rb') as f:
                data = f.read().decode('utf-8').strip()
                if data.isdigit():
                    priority = data
                    if len(priority) == 1:
                        priority = '0' + priority

        if priority is None:
            priority = '50'

        code = None
        is_py_loader = os.path.exists(loader_py_path)
        is_code_loader = os.path.exists(loader_code_path)
        if is_py_loader or is_code_loader:
            loader_path = loader_code_path if is_code_loader else loader_py_path
            with open(loader_path, 'rb') as f:
                code = f.read()

        loader.add(priority, dependency, code)

        sublime.status_message(('Dependency %s successfully added to ' +
            'dependency loader - restarting Sublime Text may be required') %
            dependency)
