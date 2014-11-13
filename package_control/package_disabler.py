import sublime

from .settings import preferences_filename
from .package_io import package_file_exists


class PackageDisabler():
    old_color_scheme_package = None
    old_color_scheme = None

    old_theme_package = None
    old_theme = None

    old_syntaxes = None

    def disable_packages(self, packages):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param packages: The string package name, or an array of strings
        """

        if not isinstance(packages, list):
            packages = [packages]

        # Don't disable Package Control so it does not get stuck disabled
        if 'Package Control' in packages:
            packages.remove('Package Control')

        disabled = []

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            ignored = []

        self.old_syntaxes = {}

        for package in packages:
            if not package in ignored:
                ignored.append(package)
                disabled.append(package)

            for window in sublime.windows():
                for view in window.views():
                    view_settings = view.settings()
                    syntax = view_settings.get('syntax')
                    if syntax.find('Packages/' + package + '/') != -1:
                        if package not in self.old_syntaxes:
                            self.old_syntaxes[package] = []
                        self.old_syntaxes[package].append([view, syntax])
                        view_settings.set('syntax', 'Packages/Text/Plain text.tmLanguage')

            # Change the color scheme before disabling the package containing it
            if settings.get('color_scheme').find('Packages/' + package + '/') != -1:
                self.old_color_scheme_package = package
                self.old_color_scheme = settings.get('color_scheme')
                settings.set('color_scheme', 'Packages/Color Scheme - Default/Monokai.tmTheme')

            # Change the theme before disabling the package containing it
            if package_file_exists(package, settings.get('theme')):
                self.old_theme_package = package
                self.old_theme = settings.get('theme')
                settings.set('theme', 'Default.sublime-theme')

        settings.set('ignored_packages', ignored)
        sublime.save_settings(preferences_filename())
        return disabled

    def reenable_package(self, package, type='upgrade'):
        """
        Re-enables a package after it has been installed or upgraded

        :param package:
            The string package name

        :param type:
            The type of operation that caused the package to be re-enabled:
             - "upgrade"
             - "removal"
             - "install"
             - "enable"
        """

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            return

        if package in ignored:
            settings.set('ignored_packages',
                list(set(ignored) - set([package])))

            if type == 'upgrade' and package in self.old_syntaxes:
                for view_syntax in self.old_syntaxes[package]:
                    view, syntax = view_syntax
                    view.settings().set('syntax', syntax)

            if type == 'upgrade' and self.old_theme_package == package:
                settings.set('theme', self.old_theme)
                sublime.message_dialog(u"Package Control\n\n" +
                    u"Your active theme was just upgraded. You may see some " +
                    u"graphical corruption until you restart Sublime Text.")

            if type == 'upgrade' and self.old_color_scheme_package == package:
                settings.set('color_scheme', self.old_color_scheme)

            if type == 'removal' and self.old_theme_package == package:
                sublime.message_dialog(u"Package Control\n\n" +
                    u"Your active theme was just removed and the Default " +
                    u"theme was enabled in its place. You may see some " +
                    u"graphical corruption until you restart Sublime Text.")

            sublime.save_settings(preferences_filename())
