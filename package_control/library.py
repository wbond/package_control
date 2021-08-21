import os
import re
import shutil

from .distinfo import DistInfoDir, find_dist_info_dir


def _name_from_dist_info_dirname(dirname):
    library_name = dirname[:-10]
    return re.sub(
        r'-(?:'
        r'(\d+(?:\.\d+)*)'
        r'([-._]?(?:alpha|a|beta|b|preview|pre|c|rc)\.?\d*)?'
        r'(-\d+|(?:[-._]?(?:rev|r|post)\.?\d*))?'
        r'([-._]?dev\.?\d*)?'
        r')$',
        '',
        library_name,
        count=1
    )


def list_all(install_root):
    """
    List all dependencies installed

    :param install_root:
        A unicode path to the directory that contains all libraries

    :return:
        A list of unicode strings containing library names
    """

    out = []
    for filename in os.listdir(install_root):
        if not filename.endswith(".dist-info"):
            continue
        path = os.path.join(install_root, filename)
        if not os.path.isdir(path):
            continue
        record_path = os.path.join(path, 'RECORD')
        if not os.path.isfile(record_path):
            continue
        out.append(_name_from_dist_info_dirname(filename))
    return out


def list_unmanaged(install_root):
    """
    List all dependencies installed that Package Control didn't install

    :param install_root:
        A unicode path to the directory that contains all libraries

    :return:
        A list of unicode strings containing library names
    """

    out = []
    for filename in os.listdir(install_root):
        if not filename.endswith(".dist-info"):
            continue
        path = os.path.join(install_root, filename)
        if not os.path.isdir(path):
            continue
        installer_path = os.path.join(path, 'INSTALLER')
        if not os.path.isfile(installer_path):
            continue

        # We ignore what we've installed since we want unmanaged libraries
        with open(installer_path, 'r', encoding='utf-8') as f:
            if f.read().strip().startswith('Package Control'):
                continue

        out.append(_name_from_dist_info_dirname(filename))
    return out


def install(dest_root, src_dir, name, version, description, url, plat_specific):
    """
    :param dest_root:
        A unicode path to the directory to install the library into. If a
        library has a folder named A, it will be installed to: dest_root/A.

    :param src_dir:
        A unicode path to the directory to copy files and folders from. For
        most libraries, this directory will contain a single folder with
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
    """
    Deletes all of the files from a library

    :param install_root:
        A unicode string of directory libraries are installed in

    :param name:
        A unicode string of the library name

    :raises:
        OSError - when a permission error occurs trying to remove a file
    """

    dist_info = find_dist_info_dir(install_root, name)

    for rel_path in dist_info.top_level_paths():
        # Remove the .dist-info dir last so we have info for cleanup in case
        # we hit an error along the way
        if rel_path == dist_info.dir_name:
            continue

        abs_path = os.path.join(dist_info.install_root, rel_path)

        if not os.path.exists(abs_path):
            continue

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.unlink(abs_path)

    abs_path = os.path.join(dist_info.install_root, dist_info.dir_name)
    if os.path.exists(abs_path):
        shutil.rmtree(abs_path)
