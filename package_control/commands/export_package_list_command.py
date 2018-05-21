import sublime
import sublime_plugin

from ..package_manager import PackageManager


class ExportPackageListCommand(sublime_plugin.WindowCommand):
    def run(self):
        manager = PackageManager()
        packages = manager.list_packages()
        packages.remove("Package Control")

        view = self.window.new_file()
        view.run_command("insert_snippet", {
            "contents": "# Use Package Control: Advanced Install Package and paste the list\n\n%s"
            % ",".join(packages)
            })

