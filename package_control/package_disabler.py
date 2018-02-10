import json

import sublime

from .console_write import console_write
from .package_io import package_file_exists
from .package_io import read_package_file
from .settings import load_list_setting
from .settings import pc_settings_filename
from .settings import preferences_filename
from .settings import save_list_setting
from .show_error import show_error
from .show_error import show_message

# This has to be imported this way for consistency with the public API,
# otherwise this code and packages will each load a different instance of the
# module, and the event tracking won't work. However, upon initial install,
# when running ST3, the module will not yet be imported, and the cwd will not
# be Packages/Package Control/ so we need to patch it into sys.modules.
try:
    from package_control import events
except (ImportError):
    events = None


class PackageDisabler(object):
    old_color_scheme_package = None
    old_color_scheme = None

    old_theme_package = None
    old_theme = None

    old_syntaxes = None
    old_color_schemes = None

    def get_version(self, package):
        """
        Gets the current version of a package

        :param package:
            The name of the package

        :return:
            The string version
        """
        metadata_json = read_package_file(package, 'package-metadata.json')
        if metadata_json:
            try:
                return json.loads(metadata_json).get('version', 'unknown version')
            except (ValueError):
                pass

        return 'unknown version'

    def disabled_packages(self):
        """
        Return the list of disabled packages.
        """
        settings = sublime.load_settings(preferences_filename())
        return load_list_setting(settings, 'ignored_packages')

    def disable_packages(self, packages, type='upgrade'):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param packages:
            The string package name, or an array of strings

        :param type:
            The type of operation that caused the package to be disabled:
             - "upgrade"
             - "remove"
             - "install"
             - "disable"
             - "loader"

        :return:
            A list of package names that were disabled
        """

        global events

        if events is None:
            from package_control import events

        if not isinstance(packages, list):
            packages = [packages]

        disabled = []

        settings = sublime.load_settings(preferences_filename())
        ignored = load_list_setting(settings, 'ignored_packages')

        pc_settings = sublime.load_settings(pc_settings_filename())
        in_process = load_list_setting(pc_settings, 'in_process_packages')

        PackageDisabler.old_color_scheme_package = None
        PackageDisabler.old_color_scheme = None

        PackageDisabler.old_theme_package = None
        PackageDisabler.old_theme = None

        PackageDisabler.old_syntaxes = {}
        PackageDisabler.old_color_schemes = {}

        for package in packages:
            if package not in ignored:
                in_process.append(package)
                ignored.append(package)
                disabled.append(package)

            if type in ('upgrade', 'remove'):
                version = self.get_version(package)
                tracker_type = 'pre_upgrade' if type == 'upgrade' else type
                events.add(tracker_type, package, version)

            package_path = 'Packages/%s/' % package

            global_color_scheme = settings.get('color_scheme')
            if global_color_scheme and package_path in global_color_scheme:
                PackageDisabler.old_color_scheme_package = package
                PackageDisabler.old_color_scheme = global_color_scheme
                settings.set('color_scheme', 'Packages/Color Scheme - Default/Monokai.tmTheme')

            for window in sublime.windows():
                for view in window.views():
                    view_settings = view.settings()
                    syntax = view_settings.get('syntax')
                    if syntax and package_path in syntax:
                        PackageDisabler.old_syntaxes.setdefault(package, []).append([view, syntax])
                        view_settings.set('syntax', 'Packages/Text/Plain text.tmLanguage')

                    # Handle view-specific color_scheme settings not already taken care
                    # of by resetting the global color_scheme above
                    scheme = view_settings.get('color_scheme')
                    if scheme and scheme != global_color_scheme and package_path in scheme:
                        PackageDisabler.old_color_schemes.setdefault(package, []).append([view, scheme])
                        view_settings.erase('color_scheme')

            # Change the theme before disabling the package containing it
            if package_file_exists(package, settings.get('theme')):
                PackageDisabler.old_theme_package = package
                PackageDisabler.old_theme = settings.get('theme')
                settings.set('theme', 'Default.sublime-theme')

        # We don't mark a package as in-process when disabling it, otherwise
        # it automatically gets re-enabled the next time Sublime Text starts
        if type != 'disable':
            save_list_setting(pc_settings, pc_settings_filename(), 'in_process_packages', in_process)

        save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

        return disabled

    def reenable_package(self, package, type='upgrade'):
        """
        Re-enables a package after it has been installed or upgraded

        :param package:
            The string package name

        :param type:
            The type of operation that caused the package to be re-enabled:
             - "upgrade"
             - "remove"
             - "install"
             - "enable"
             - "loader"
        """

        global events

        if events is None:
            from package_control import events

        settings = sublime.load_settings(preferences_filename())
        ignored = load_list_setting(settings, 'ignored_packages')

        if package in ignored:

            if type in ('install', 'upgrade'):
                version = self.get_version(package)
                tracker_type = 'post_upgrade' if type == 'upgrade' else type
                events.add(tracker_type, package, version)
                events.clear(tracker_type, package, future=True)
                if type == 'upgrade':
                    events.clear('pre_upgrade', package)

            elif type == 'remove':
                events.clear('remove', package)

            ignored = list(set(ignored) - set([package]))
            save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

            if type == 'remove' and PackageDisabler.old_theme_package == package:
                show_message(
                    '''
                    The package containing your active theme was just removed
                    and the Default theme was enabled in its place.
                    '''
                )

            # By delaying the restore, we give Sublime Text some time to
            # re-enable the package, making errors less likely
            def delayed_settings_restore():
                syntax_errors = set()
                color_scheme_errors = set()

                if PackageDisabler.old_syntaxes is None:
                    PackageDisabler.old_syntaxes = {}
                if PackageDisabler.old_color_schemes is None:
                    PackageDisabler.old_color_schemes = {}

                if type == 'upgrade' and package in PackageDisabler.old_syntaxes:
                    for view_syntax in PackageDisabler.old_syntaxes[package]:
                        view, syntax = view_syntax
                        if resource_exists(syntax):
                            view.settings().set('syntax', syntax)
                        elif syntax not in syntax_errors:
                            console_write('The syntax "%s" no longer exists' % syntax)
                            syntax_errors.add(syntax)

                if type == 'upgrade' and PackageDisabler.old_color_scheme_package == package:
                    if resource_exists(PackageDisabler.old_color_scheme):
                        settings.set('color_scheme', PackageDisabler.old_color_scheme)
                    else:
                        color_scheme_errors.add(PackageDisabler.old_color_scheme)
                        show_error(
                            '''
                            The package containing your active color scheme was
                            just upgraded, however the .tmTheme file no longer
                            exists. Sublime Text has been configured use the
                            default color scheme instead.
                            '''
                        )

                if type == 'upgrade' and package in PackageDisabler.old_color_schemes:
                    for view_scheme in PackageDisabler.old_color_schemes[package]:
                        view, scheme = view_scheme
                        if resource_exists(scheme):
                            view.settings().set('color_scheme', scheme)
                        elif scheme not in color_scheme_errors:
                            console_write('The color scheme "%s" no longer exists' % scheme)
                            color_scheme_errors.add(scheme)

                if type == 'upgrade' and PackageDisabler.old_theme_package == package:
                    if package_file_exists(package, PackageDisabler.old_theme):
                        settings.set('theme', PackageDisabler.old_theme)
                        show_message('The package containing your active theme was just upgraded.')
                    else:
                        show_error(
                            '''
                            The package containing your active theme was just
                            upgraded, however the .sublime-theme file no longer
                            exists. Sublime Text has been configured use the
                            default theme instead.
                            '''
                        )

                sublime.save_settings(preferences_filename())

            sublime.set_timeout(delayed_settings_restore, 1000)

        pc_settings = sublime.load_settings(pc_settings_filename())
        in_process = load_list_setting(pc_settings, 'in_process_packages')

        if package in in_process:
            in_process.remove(package)
            save_list_setting(pc_settings, pc_settings_filename(), 'in_process_packages', in_process)


def resource_exists(path):
    """
    Checks to see if a file exists

    :param path:
        A unicode string of a resource path, e.g. Packages/Package Name/resource_name.ext

    :return:
        A bool if it exists
    """

    if not path.startswith('Packages/'):
        return False

    parts = path[9:].split('/', 1)
    if len(parts) != 2:
        return False

    package_name, relative_path = parts
    return package_file_exists(package_name, relative_path)
