import html
import sublime
import sublime_plugin

from package_control.package_disabler import PackageDisabler
from package_control.package_manager import PackageManager


sheet = None


def plugin_loaded():
    PackageListener.start()

def plugin_unloaded():
    PackageListener.stop()


class PackageListener:
    _ignored = []
    _settings = None
    _uuid = "5b991c43-d049-4ac7-878e-c22f201a4b3c"

    @classmethod
    def settings(cls):
        return sublime.load_settings("Preferences.sublime-settings")

    @classmethod
    def start(cls):
        if cls._settings is None:
            cls._settings = sublime.load_settings("Preferences.sublime-settings")
            cls._ignored = cls._settings.get("ignored_packages", [])
            cls._settings.add_on_change(cls._uuid, cls._on_change)

    @classmethod
    def stop(cls):
        if cls._settings is not None:
            cls.settings().clear_on_change(cls._uuid)
            cls._settings = None

    @classmethod
    def _on_change(cls):
        if not cls._settings:
            return

        ignored = cls._settings.get("ignored_packages", [])
        if ignored == cls._ignored:
            return

        cls._ignored = ignored
        sublime.run_command("show_package_report", {"update_only": True})


class ShowPackageReportCommand(sublime_plugin.ApplicationCommand):

    def run(self, update_only=False):
        global sheet

        window = sublime.active_window()
        if not window:
            return

        if update_only:
            if sheet is None or sheet.window() is None:
                return

        package_manager = PackageManager()

        content = """
        <html>
        <body id="package_control">
        <style>
        body {
            font-family: Segoe UI, Arial, Helvetica;
        }
        h2 {
            color: color(var(--foreground) blend(var(--background) 50%));
            font-size: 1.2rem;
            font-weight: normal;
            margin-bottom: 4pt;
            padding-bottom: 0px;
        }
        h3 {
            color: color(var(--foreground) blend(var(--background) 80%));
            font-size: 1.0rem;
            font-weight: normal;
            margin-bottom: 4pt;
            padding-bottom: 0px;
        }
        ul {
            margin: 0px;
            padding-left: 1rem;
        }
        a {
            text-decoration: none;
        }
        .p-meta {
            color: color(var(--foreground) blend(var(--background) 65%));
            font-family: monospace;
            font-size: 0.75rem;
        }
        .p-menu {
            color: color(var(--foreground) blend(var(--background) 65%));
            font-family: monospace;
            font-size: 0.75rem;
            margin-top: 10pt;
        }
        .p-body {
            margin-left: 8pt;
        }
        .p-enabled {
            color: var(--greenish);
        }
        .sep {
            color: var(--accent);
        }
        </style>
        """

        disabled_packages = PackageDisabler.ignored_packages()

        package_htmls = []

        for package in sorted(package_manager.list_packages(), key=lambda s: s.lower()):
            p_html = "<h2>" + package + "</h2>"

            # meta data line
            meta = package_manager.get_metadata(package)

            p_html += '<div class="p-meta">'
            is_enabled = package not in disabled_packages
            if is_enabled:
                p_html += '<span class="p-enabled">◼</span>'
            else:
                p_html += '<span class="p-disabled">◻</span>'
            p_html += ' <span class="sep">|</span> '
            p_html += meta.get("version", "unknown")
            p_html += ' <span class="sep">|</span> '
            p_html += "py " + str(package_manager.get_python_version(package))
            p_html += ' <span class="sep">|</span> '
            p_html += "managed" if package_manager.is_managed(package) else "unmanaged"

            url = meta.get("url")
            if url:
                p_html += ' <span class="sep">|</span> '
                p_html += '<a href="' + url + '">' + url + "</a>"

            p_html += "</div>"

            # commands
            p_html += '<div class="p-menu">'
            if is_enabled:
                p_html += '[ <a href="' + sublime.command_url("disable_packages", {"packages": [package]}) + '">disable</a> ]'
            else:
                p_html += '[ <a href="' + sublime.command_url("enable_packages", {"packages": [package]}) + '">enable</a> ]'
            p_html += ' '
            p_html += '[ <a href="' + sublime.command_url("remove_packages", {"packages": [package]}) + '">remove</a> ]'

            p_html += "</div>"

            # package body
            p_html += '<div class="p-body">'
            p_html += (
                "<p>" + html.escape(meta.get("description", "no description")) + "</p>"
            )

            libraries = package_manager.get_libraries(package)
            if libraries:
                p_html += "<h3>Requirements:</h3>"
                p_html += "<ul>"

                for library in sorted(libraries, key=lambda s: s.name.lower()):
                    p_html += "<li>" + library.name + "</li>"

                p_html += "</ul>"

            p_html += "</div>"

            package_htmls.append(p_html)

        content += "".join(package_htmls)
        content += "</body>"
        content += "</html>"

        if sheet is None or sheet.window() is None:
            window = sublime.active_window()
            if not window:
                window = sublime.windows()[0]

            sheet = window.new_html_sheet("Package Details", content)

        else:
            sheet.set_contents(content)
