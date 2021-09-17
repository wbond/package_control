import os
import sys
import tempfile
import unittest

from .. import distinfo
from .. import __version__


tmp_dir = tempfile.TemporaryDirectory


def _tag(version):
    if sys.platform == "darwin":
        if version == "3.3":
            tag = "macosx_10_7_%s" % os.uname()[4]
        elif version == "3.8":
            tag = "macosx_10_9_%s" % os.uname()[4]
        else:
            raise ValueError("Invalid version")
    elif sys.platform == "linux":
        tag = "linux_%s" % os.uname()[4]
    else:
        if sys.maxsize == 2147483647:
            tag = "win32"
        else:
            tag = "win_amd64"
    return tag


def _create_package_files(d):
    main_py = os.path.join(d, 'testing.py')
    module_dir = os.path.join(d, 'testing')
    submodule1 = os.path.join(module_dir, 'submod1.py')
    submodule2 = os.path.join(module_dir, 'submod2.py')

    os.mkdir(module_dir)

    with open(main_py, 'w', encoding='utf-8', newline='\n') as f:
        f.write(
            "print('Hello world!')\n"
            "\n"
            "import testing.submod1\n"
            "import testing.submod2\n"
        )

    with open(submodule1, 'w', encoding='utf-8', newline='\n') as f:
        f.write("print('Do you like my hat?')")

    with open(submodule2, 'w', encoding='utf-8', newline='\n') as f:
        f.write("print('I do not like your hat!')")

    return ([module_dir], ['testing.py'])


def _create_package_files_2(d):
    module_dir = os.path.join(d, 'testing')
    submodule1 = os.path.join(module_dir, 'submod1.py')
    submodule2 = os.path.join(module_dir, 'submod2.py')

    os.mkdir(module_dir)

    with open(submodule1, 'w', encoding='utf-8', newline='\n') as f:
        f.write("print('Do you like my hat?')")

    with open(submodule2, 'w', encoding='utf-8', newline='\n') as f:
        f.write("print('I do not like your hat!')")

    return ([module_dir], [])


class DistinfoTests(unittest.TestCase):
    def test_distinfo(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'
            os.mkdir(os.path.join(d, did_name))

            did = distinfo.DistInfoDir(d, did_name)
            self.assertEqual(True, did.exists())

    def test_distinfo_make_dir(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            self.assertEqual(False, did.exists())
            did.ensure_exists()
            self.assertEqual(True, did.exists())

    def test_distinfo_write_metadata(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )
            metadata_path = os.path.join(d, did_name, "METADATA")
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.assertEqual(
                    "Metadata-Version: 2.1\n"
                    "Name: testing\n"
                    "Version: 1.0.0\n"
                    "Summary: A testing package\n"
                    "Home-page: http://example.com\n",
                    f.read()
                )

    def test_distinfo_read_metadata(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )

            self.assertEqual(
                {
                    "metadata-version": "2.1",
                    "name": "testing",
                    "version": "1.0.0",
                    "summary": "A testing package",
                    "home-page": "http://example.com",
                },
                did.read_metadata()
            )

    def test_distinfo_write_installer(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_installer()
            installer_path = os.path.join(d, did_name, "INSTALLER")
            with open(installer_path, "r", encoding="utf-8") as f:
                self.assertEqual(
                    "Package Control\n",
                    f.read()
                )

    def test_distinfo_read_installer(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_installer()
            self.assertEqual(
                "Package Control",
                did.read_installer()
            )

    def test_distinfo_write_wheel_invalid(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            with self.assertRaises(ValueError):
                did.write_wheel("3.4", False)

    def test_distinfo_write_wheel_33_generic(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_wheel("3.3", False)
            wheel_path = os.path.join(d, did_name, "WHEEL")
            with open(wheel_path, "r", encoding="utf-8") as f:
                self.assertEqual(
                    (
                        "Wheel-Version: 1.0\n"
                        "Generator: Package Control (%s)\n"
                        "Root-Is-Purelib: true\n"
                        "Tag: py33-none-any\n"
                    ) % (__version__,),
                    f.read()
                )

    def test_distinfo_write_wheel_33_plat(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_wheel("3.3", True)
            wheel_path = os.path.join(d, did_name, "WHEEL")
            with open(wheel_path, "r", encoding="utf-8") as f:
                self.assertEqual(
                    (
                        "Wheel-Version: 1.0\n"
                        "Generator: Package Control (%s)\n"
                        "Root-Is-Purelib: true\n"
                        "Tag: py33-cp33m-%s\n"
                    ) % (__version__, _tag("3.3")),
                    f.read()
                )

    def test_distinfo_write_wheel_38_generic(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_wheel("3.8", False)
            wheel_path = os.path.join(d, did_name, "WHEEL")
            with open(wheel_path, "r", encoding="utf-8") as f:
                self.assertEqual(
                    (
                        "Wheel-Version: 1.0\n"
                        "Generator: Package Control (%s)\n"
                        "Root-Is-Purelib: true\n"
                        "Tag: py38-none-any\n"
                    ) % (__version__,),
                    f.read()
                )

    def test_distinfo_write_wheel_38_plat(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_wheel("3.8", True)
            wheel_path = os.path.join(d, did_name, "WHEEL")
            with open(wheel_path, "r", encoding="utf-8") as f:
                self.assertEqual(
                    (
                        "Wheel-Version: 1.0\n"
                        "Generator: Package Control (%s)\n"
                        "Root-Is-Purelib: true\n"
                        "Tag: py38-cp38m-%s\n"
                    ) % (__version__, _tag("3.8")),
                    f.read()
                )

    def test_distinfo_write_record(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            package_dirs, package_files = _create_package_files(d)

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )
            did.write_installer()
            did.write_wheel("3.8", False)
            did.write_record(package_dirs, package_files)
            record_path = os.path.join(d, did_name, "RECORD")
            with open(record_path, "r", encoding="utf-8") as f:
                self.maxDiff = None
                self.assertEqual(
                    "testing-1.0.0.dist-info/INSTALLER,sha256=Hg_Q6w_I4zpFfb6C24LQdd4oTAMHJZDk9gtuV2yOgkw,16\n"
                    "testing-1.0.0.dist-info/METADATA,sha256=eYkwWwXPP3gmZteGofvQDKR76W24np070-bgFO7_eRk,108\n"
                    "testing-1.0.0.dist-info/RECORD,,\n"
                    "testing-1.0.0.dist-info/WHEEL,sha256=bnuWs1vbOwvsSNtu5ecmSmNp-TSIDAMQi00d5kxrrEg,99\n"
                    "testing.py,sha256=x70rG6LT6Ztax8UDBo07_fpElW9j47oz6MRkKFeOUuM,69\n"
                    "testing/submod1.py,sha256=Fq_s7atiTPeHUzEe56JA8IDbPqlntBpHVfJchJ6C31M,28\n"
                    "testing/submod2.py,sha256=RWIeIEzzpcpqdk9TW1HRFQltzMY7WxT8tX2NQsqfyYE,32\n",
                    f.read()
                )

    def test_distinfo_read_record(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            package_dirs, package_files = _create_package_files(d)

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )
            did.write_installer()
            did.write_wheel("3.8", False)
            did.write_record(package_dirs, package_files)

            record_infos = did.read_record()
            self.assertEqual(7, len(record_infos))

            self.assertEqual("testing-1.0.0.dist-info/INSTALLER", record_infos[0].relative_path)
            self.assertEqual("Hg_Q6w_I4zpFfb6C24LQdd4oTAMHJZDk9gtuV2yOgkw", record_infos[0].sha256)
            self.assertEqual(16, record_infos[0].size)

            self.assertEqual("testing-1.0.0.dist-info/METADATA", record_infos[1].relative_path)
            self.assertEqual("eYkwWwXPP3gmZteGofvQDKR76W24np070-bgFO7_eRk", record_infos[1].sha256)
            self.assertEqual(108, record_infos[1].size)

            self.assertEqual("testing-1.0.0.dist-info/RECORD", record_infos[2].relative_path)
            self.assertEqual(None, record_infos[2].sha256)
            self.assertEqual(None, record_infos[2].size)

            self.assertEqual("testing-1.0.0.dist-info/WHEEL", record_infos[3].relative_path)
            self.assertEqual("bnuWs1vbOwvsSNtu5ecmSmNp-TSIDAMQi00d5kxrrEg", record_infos[3].sha256)
            self.assertEqual(99, record_infos[3].size)

            self.assertEqual("testing.py", record_infos[4].relative_path)
            self.assertEqual("x70rG6LT6Ztax8UDBo07_fpElW9j47oz6MRkKFeOUuM", record_infos[4].sha256)
            self.assertEqual(69, record_infos[4].size)

            self.assertEqual("testing/submod1.py", record_infos[5].relative_path)
            self.assertEqual("Fq_s7atiTPeHUzEe56JA8IDbPqlntBpHVfJchJ6C31M", record_infos[5].sha256)
            self.assertEqual(28, record_infos[5].size)

            self.assertEqual("testing/submod2.py", record_infos[6].relative_path)
            self.assertEqual("RWIeIEzzpcpqdk9TW1HRFQltzMY7WxT8tX2NQsqfyYE", record_infos[6].sha256)
            self.assertEqual(32, record_infos[6].size)

    def test_distinfo_top_level_paths(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            package_dirs, package_files = _create_package_files(d)

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )
            did.write_installer()
            did.write_wheel("3.8", False)
            did.write_record(package_dirs, package_files)

            paths = did.top_level_paths()
            self.assertEqual(3, len(paths))
            self.assertEqual(
                [
                    "testing",
                    "testing-1.0.0.dist-info",
                    "testing.py",
                ],
                paths
            )

    def test_distinfo_top_level_paths_2(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            package_dirs, package_files = _create_package_files_2(d)

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )
            did.write_installer()
            did.write_wheel("3.8", False)
            did.write_record(package_dirs, package_files)

            paths = did.top_level_paths()
            self.assertEqual(2, len(paths))
            self.assertEqual(
                [
                    "testing",
                    "testing-1.0.0.dist-info",
                ],
                paths
            )

    def test_distinfo_verify_files(self):
        with tmp_dir() as d:
            did_name = 'testing-1.0.0.dist-info'

            package_dirs, package_files = _create_package_files(d)

            did = distinfo.DistInfoDir(d, did_name)
            did.ensure_exists()
            did.write_metadata(
                "testing",
                "1.0.0",
                "A testing package",
                "http://example.com"
            )
            did.write_installer()
            did.write_wheel("3.8", False)
            did.write_record(package_dirs, package_files)

            unmodified, modified = did.verify_files()
            self.assertEqual(0, len(modified))
            self.assertEqual(7, len(unmodified))

            sorted_records = sorted(list(unmodified), key=lambda ri: ri.relative_path)

            self.assertEqual("testing-1.0.0.dist-info/INSTALLER", sorted_records[0].relative_path)
            self.assertEqual("Hg_Q6w_I4zpFfb6C24LQdd4oTAMHJZDk9gtuV2yOgkw", sorted_records[0].sha256)
            self.assertEqual(16, sorted_records[0].size)

            self.assertEqual("testing-1.0.0.dist-info/METADATA", sorted_records[1].relative_path)
            self.assertEqual("eYkwWwXPP3gmZteGofvQDKR76W24np070-bgFO7_eRk", sorted_records[1].sha256)
            self.assertEqual(108, sorted_records[1].size)

            self.assertEqual("testing-1.0.0.dist-info/RECORD", sorted_records[2].relative_path)
            self.assertEqual(None, sorted_records[2].sha256)
            self.assertEqual(None, sorted_records[2].size)

            self.assertEqual("testing-1.0.0.dist-info/WHEEL", sorted_records[3].relative_path)
            self.assertEqual("bnuWs1vbOwvsSNtu5ecmSmNp-TSIDAMQi00d5kxrrEg", sorted_records[3].sha256)
            self.assertEqual(99, sorted_records[3].size)

            self.assertEqual("testing.py", sorted_records[4].relative_path)
            self.assertEqual("x70rG6LT6Ztax8UDBo07_fpElW9j47oz6MRkKFeOUuM", sorted_records[4].sha256)
            self.assertEqual(69, sorted_records[4].size)

            self.assertEqual("testing/submod1.py", sorted_records[5].relative_path)
            self.assertEqual("Fq_s7atiTPeHUzEe56JA8IDbPqlntBpHVfJchJ6C31M", sorted_records[5].sha256)
            self.assertEqual(28, sorted_records[5].size)

            self.assertEqual("testing/submod2.py", sorted_records[6].relative_path)
            self.assertEqual("RWIeIEzzpcpqdk9TW1HRFQltzMY7WxT8tX2NQsqfyYE", sorted_records[6].sha256)
            self.assertEqual(32, sorted_records[6].size)
