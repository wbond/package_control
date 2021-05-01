import os
import shutil

from .distinfo import DistInfoDir, find_dist_info_dir


def install(dest_root, src_dir, name, version, description, url, plat_specific):
    """
    :param dest_root:
        A unicode path to the directory to install the library into. If a
        library has a folder named A, it will be installed to: dest_root/A.

    :param src_dir:
        A unicode path to the directory to copy files and folders from. For
        most dependencies, this directory will contain a single folder with
        the name of the library.

    :param name:
        A unicode string of the library name

    :param version:
        A unicode string of a PEP 440 version

    :param description:
        An optional unicode string of a description of the library

    :param url:
        An optional unicode string of the homepage for the library

    :param plat_specific:
        A bool indicating if the source files are platform or architecture
        specific. Typically this would be set if the library contains any
        shared libraries or executables.
    """

    dist_info_dirname = '%s-%s.dist-info' % (name, version)
    dist_info = DistInfoDir(dest_root, dist_info_dirname)

    extra_filenames = dist_info.extra_files()
    shared_exts = dist_info.shared_lib_extensions()

    # TEMP - linter
    # found_license = False
    # found_readme = False

    package_dirs = []
    package_files = []
    for fname in os.listdir(src_dir):
        path = os.path.join(src_dir, fname)
        ext = os.path.splitext(fname)[-1]
        lf = fname.lower()
        if os.path.isdir(path):
            package_dirs.append((fname, path))
        elif ext == '.py':
            package_files.append((fname, path))
        elif ext in shared_exts:
            package_files.append((fname, path))
        elif lf in extra_filenames:
            # Extra files in the root need to be put into the
            # .dist-info dir since that is the only place we can
            # ensure there won't be name conflicts
            package_files.append(('%s/%s' % (dist_info_dirname, fname), path))
            # TEMP - linter
            # if 'readme' in lf:
            #     found_readme = True
            # if 'license' in lf:
            #     found_license = True

    dist_info.ensure_exists()
    dist_info.write_wheel('3.3', plat_specific)
    dist_info.write_metadata(name, version, description, url)
    dist_info.write_installer()

    package_dir_names = []
    for dname, source in package_dirs:
        package_dir_names.append(dname)
        shutil.copytree(source, os.path.join(dest_root, dname))

    package_file_names = []
    for rel_dest, source in package_files:
        if '/' not in rel_dest:
            package_file_names.append(rel_dest)
        with open(source, 'rb') as sf:
            with open(os.path.join(dest_root, rel_dest), 'wb') as df:
                df.write(sf.read())

    dist_info.write_record(package_dir_names, package_file_names)


def remove(install_root, name):
    dist_info = find_dist_info_dir(install_root, name)

    dir_names = set()

    try:
        record = dist_info.read_record()
    except FileNotFoundError:
        raise FileNotFoundError('Library {} not installed!'.format(name))

    for file_name, file_hash, file_size in record:
        abs_path = os.path.normpath(os.path.join(install_root, file_name))
        dir_names.add(os.path.dirname(abs_path))
        print("removing", abs_path)
        # os.remove(abs_path)

    def sort_key(a):
        return len(a.split(os.sep))

    for dir_name in sorted(dir_names, key=sort_key, reverse=True):
        print("removing", dir_name)
        # os.remove(dirname)
