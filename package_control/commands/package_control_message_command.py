import sublime_plugin


class PackageControlMessageCommand(sublime_plugin.TextCommand):
    view_name = "Package Control Messages"

    def run(self, edit, message):
        if self.view.name() != self.view_name:
            return

        eof = self.view.size()
        if eof == 0:
            message = "{}\n{}\n{}".format(
                self.view_name, "=" * len(self.view_name), message
            )

        self.view.set_read_only(False)
        self.view.insert(edit, eof, message)
        self.view.set_read_only(True)
