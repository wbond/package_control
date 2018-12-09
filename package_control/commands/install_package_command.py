import threading

import sublime
import sublime_plugin

from .advanced_install_package_command import AdvancedInstallPackageThread

from .. import text
from ..show_quick_panel import show_quick_panel
from ..package_installer import PackageInstaller
from ..thread_progress import ThreadProgress


class InstallPackageCommand(sublime_plugin.WindowCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        thread = InstallPackageThread(self.window)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class InstallPackageThread(threading.Thread, PackageInstaller):

    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the available package list in.
        """
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

        self.window = window
        self.completion_type = 'installed'

        self.exclusion_flag   = " (excluded)"
        self.inclusion_flag   = " (selected)"
        self.last_picked_item = 0
        self.last_excluded_items = 0

    def run(self):
        self.repositories_list = [ ["", "", ""] ]
        self.repositories_list.extend( self.make_package_list( ignore_packages=["PackagesManager", "Package Control"] ) )

        self.update_start_item_name()
        self.repositories_list[0][2] = "(from {length} packages available)".format( length=len( self.repositories_list ) - 1 )

        if len( self.repositories_list ) < 2:
            sublime.message_dialog(text.format(
                u'''
                Package Control

                There are no packages available for installation

                Please see https://packagecontrol.io/docs/troubleshooting
                for help
                '''
            ))
            return

        show_quick_panel( self.window, self.repositories_list, self.on_done )

    def on_done(self, picked_index):

        if picked_index < 0:
            return

        if picked_index == 0:

            # No repositories selected, reshow the menu
            if self.get_total_items_selected() < 1:
                show_quick_panel( self.window, self.repositories_list, self.on_done )

            else:
                packages = []

                for index in range( 1, self.last_picked_item + 1 ):
                    package_name = self.repositories_list[index][0]

                    if package_name.endswith( self.exclusion_flag ):
                        continue

                    if package_name.endswith( self.inclusion_flag ):
                        package_name = package_name[:-len( self.inclusion_flag )]

                    packages.append( package_name )

                thread = AdvancedInstallPackageThread( packages )
                thread.start()

                ThreadProgress(
                    thread,
                    'Installing %s packages' % len(packages),
                    'Successfully %s %s packages' % (self.completion_type, len(packages))
                )

        else:

            if picked_index <= self.last_picked_item:
                picked_package = self.repositories_list[picked_index]

                if picked_package[0].endswith( self.inclusion_flag ):
                    picked_package[0] = picked_package[0][:-len( self.inclusion_flag )]

                if picked_package[0].endswith( self.exclusion_flag ):

                    if picked_package[0].endswith( self.exclusion_flag ):
                        picked_package[0] = picked_package[0][:-len( self.exclusion_flag )]

                    self.last_excluded_items -= 1
                    self.repositories_list[picked_index][0] = picked_package[0] + self.inclusion_flag

                else:
                    self.last_excluded_items += 1
                    self.repositories_list[picked_index][0] = picked_package[0] + self.exclusion_flag

            else:
                self.last_picked_item += 1
                self.repositories_list[picked_index][0] = self.repositories_list[picked_index][0] + self.inclusion_flag

            self.update_start_item_name()
            self.repositories_list.insert( 1, self.repositories_list.pop( picked_index ) )

            show_quick_panel( self.window, self.repositories_list, self.on_done )

    def update_start_item_name(self):
        items = self.get_total_items_selected()

        if items:
            self.repositories_list[0][0] = "Select this first item to start the installation..."

        else:
            self.repositories_list[0][0] = "Select all the packages you would like to install"

        self.repositories_list[0][1] = "(%d items selected)" % ( items )

    def get_total_items_selected(self):
        return self.last_picked_item - self.last_excluded_items
