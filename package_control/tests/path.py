import os
import unittest

import sublime

from .. import path


class PathTests(unittest.TestCase):

    def test_cache_path(self):
        pc_cache_path = os.path.join(sublime.cache_path(), 'Package Control')

        # reset the method to uninitalized state
        if hasattr(path.cache_path, 'cached'):
            delattr(path.cache_path, 'cached')

        # cache does not exist
        with self.assertRaises(AttributeError):
            cached = path.cache_path.cached

        # run the first time to initiate the cache
        self.assertEqual(path.cache_path(), pc_cache_path)

        # check cache was set
        self.assertEqual(path.cache_path.cached, pc_cache_path)

        # run the second time using the cached value
        self.assertEqual(path.cache_path(), pc_cache_path)

    def test_executable_path(self):
        executable_path = sublime.executable_path()

        # reset the method to uninitalized state
        if hasattr(path.executable_path, 'cached'):
            delattr(path.executable_path, 'cached')

        # cache does not exist
        with self.assertRaises(AttributeError):
            cached = path.executable_path.cached

        # run the first time to initiate the cache
        self.assertEqual(path.executable_path(), executable_path)

        # check cache was set
        self.assertEqual(path.executable_path.cached, executable_path)

        # run the second time using the cached value
        self.assertEqual(path.executable_path(), executable_path)

    def test_default_packages_path(self):
        default_packages_path = os.path.join(
            os.path.dirname(sublime.executable_path()), 'Packages')

        # reset the method to uninitalized state
        if hasattr(path.default_packages_path, 'cached'):
            delattr(path.default_packages_path, 'cached')

        # cache does not exist
        with self.assertRaises(AttributeError):
            cached = path.default_packages_path.cached

        # run the first time to initiate the cache
        self.assertEqual(path.default_packages_path(), default_packages_path)

        # check cache was set
        self.assertEqual(path.default_packages_path.cached, default_packages_path)

        # run the second time using the cached value
        self.assertEqual(path.default_packages_path(), default_packages_path)

    def test_installed_packages_path(self):
        installed_packages_path = sublime.installed_packages_path()

        # reset the method to uninitalized state
        if hasattr(path.installed_packages_path, 'cached'):
            delattr(path.installed_packages_path, 'cached')

        # cache does not exist
        with self.assertRaises(AttributeError):
            cached = path.installed_packages_path.cached

        # run the first time to initiate the cache
        self.assertEqual(path.installed_packages_path(), installed_packages_path)

        # check cache was set
        self.assertEqual(path.installed_packages_path.cached, installed_packages_path)

        # run the second time using the cached value
        self.assertEqual(path.installed_packages_path(), installed_packages_path)

    def test_unpacked_packages_path(self):
        unpacked_packages_path = sublime.packages_path()

        # reset the method to uninitalized state
        if hasattr(path.unpacked_packages_path, 'cached'):
            delattr(path.unpacked_packages_path, 'cached')

        # cache does not exist
        with self.assertRaises(AttributeError):
            cached = path.unpacked_packages_path.cached

        # run the first time to initiate the cache
        self.assertEqual(path.unpacked_packages_path(), unpacked_packages_path)

        # check cache was set
        self.assertEqual(path.unpacked_packages_path.cached, unpacked_packages_path)

        # run the second time using the cached value
        self.assertEqual(path.unpacked_packages_path(), unpacked_packages_path)

    def test_installed_package_path(self):
        package = 'Test Package'

        self.assertEqual(
            path.installed_package_path(package),
            os.path.join(sublime.installed_packages_path(), package + '.sublime-package')
        )

    def test_unpacked_package_path(self):
        package = 'Test Package'

        self.assertEqual(
            path.unpacked_package_path(package),
            os.path.join(sublime.packages_path(), package)
        )
