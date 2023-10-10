import os
import textwrap

import sublime
import sublime_plugin


def reformat(template):
    return textwrap.dedent(template).lstrip()


class NewChannelJsonCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.settings().set("default_dir", os.path.join(sublime.packages_path(), "User"))
        view.assign_syntax("JSON.sublime-syntax")
        view.set_name("channel.json")

        template = reformat(
            """
            {
            \t"\\$schema": "sublime://packagecontrol.io/schemas/channel",
            \t"schema_version": "4.0.0",
            \t"repositories": [
            \t\t"$0"
            \t]
            }
            """
        )
        view.run_command("insert_snippet", {"contents": template})


class NewRepositoryJsonCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.settings().set("default_dir", os.path.join(sublime.packages_path(), "User"))
        view.assign_syntax("JSON.sublime-syntax")
        view.set_name("repository.json")

        template = reformat(
            """
            {
            \t"\\$schema": "sublime://packagecontrol.io/schemas/repository",
            \t"schema_version": "4.0.0",
            \t"packages": [
            \t\t$0
            \t],
            \t"libraries": []
            }
            """
        )
        view.run_command("insert_snippet", {"contents": template})
