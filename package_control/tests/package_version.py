import unittest

from ..package_version import PackageVersion, SemVer


class PackageVersionTests(unittest.TestCase):

    def test_package_version_from_major(self):
        self.assertEqual(
            SemVer(1, 0, 0, None, None),
            PackageVersion('1')
        )

    def test_package_version_from_major_minor(self):
        self.assertEqual(
            SemVer(1, 2, 0, None, None),
            PackageVersion('1.2')
        )

    def test_package_version_from_major_minor_patch(self):
        self.assertEqual(
            SemVer(1, 2, 3, None, None),
            PackageVersion('1.2.3')
        )

    def test_package_version_from_major_minor_patch_pre(self):
        self.assertEqual(
            SemVer(1, 2, 3, 'pre', None),
            PackageVersion('1.2.3-pre')
        )

    def test_package_version_from_major_minor_patch_rc1(self):
        self.assertEqual(
            SemVer(1, 2, 3, 'rc1', None),
            PackageVersion('1.2.3-rc1')
        )

    def test_package_version_from_major_minor_patch_build(self):
        self.assertEqual(
            SemVer(1, 2, 3, None, '4'),
            PackageVersion('1.2.3.4')
        )

    def test_package_version_from_timestamp(self):
        self.assertEqual(
            SemVer(0, 0, 1, None, '2020.07.15.10.50.38'),
            PackageVersion('2020.07.15.10.50.38')
        )

    def test_package_version_from_semver(self):
        self.assertEqual(
            SemVer(1, 2, 3, None, None),
            PackageVersion(SemVer(1, 2, 3, None, None))
        )

    def test_package_version_from_release(self):
        self.assertEqual(
            SemVer(1, 2, 3, None, None),
            PackageVersion({
                'version': '1.2.3',
                'platforms': ['*'],
                'sublime_text': '*',
                'url': 'https://gitlab.com/packagecontrol-test/'
                       'package_control-tester/-/archive/master/package_control-tester-master.zip'
            })
        )

    def test_package_version_from_release_with_semver(self):
        self.assertEqual(
            SemVer(1, 2, 3, None, None),
            PackageVersion({
                'version': PackageVersion('1.2.3'),
                'platforms': ['*'],
                'sublime_text': '*',
                'url': 'https://gitlab.com/packagecontrol-test/'
                       'package_control-tester/-/archive/master/package_control-tester-master.zip'
            })
        )

    def test_package_version_from_invalid_dict(self):
        with self.assertRaises(TypeError) as cm:
            PackageVersion({'foo': 'bar'})
        self.assertEqual(
            "{'foo': 'bar'} is not a package or library release",
            str(cm.exception)
        )

    def test_package_version_from_invalid_number(self):
        with self.assertRaises(TypeError) as cm:
            PackageVersion(1.2)
        self.assertEqual(
            "1.2 is not a string",
            str(cm.exception)
        )

    def test_package_version_from_invalid_string(self):
        with self.assertRaises(ValueError) as cm:
            PackageVersion('foo')
        self.assertEqual(
            "'foo' is not a valid SemVer string",
            str(cm.exception)
        )
