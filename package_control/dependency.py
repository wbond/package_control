import os
import shutil

from . import wheel


def install(dest_root, src_dir, name, version, description, url, plat_specific):
    """
    :param dest_root:
        A unicode path to the directory to install the dependency into. If a
        dependency has a folder named A, it will be installed to: dest_root/A.

    :param src_dir:
        A unicode path to the directory to copy files and folders from. For
        most dependencies, this directory will contain a single folder with
        the name of the dependency.

    :param name:
        A unicode string of the dependency name

    :param version:
        A unicode string of a PEP 440 version

    :param description:
        An optional unicode string of a description of the dependency

    :param url:
        An optional unicode string of the homepage for the dependency

    :param plat_specific:
        A bool indicating if the source files are platform or architecture
        specific. Typically this would be set if the dependency contains any
        shared libraries or executables.
    """

    dist_info_dirname = '%s-%s.dist-info' % (name, version)
    dist_info_path = os.path.join(dest_root, dist_info_dirname)
    extra_filenames = wheel.extra_files()
    shared_exts = wheel.shared_lib_extensions()

    found_license = False
    found_readme = False

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
            if 'readme' in lf:
                found_readme = True
            if 'license' in lf:
                found_license = True

    if not os.path.exists(dist_info_path):
        os.mkdir(dist_info_path)

    di_wheel_path = os.path.join(dist_info_path, 'WHEEL')
    wf_contents = wheel.generate_wheel_file('3.3', plat_specific)
    with open(di_wheel_path, 'wb') as f:
        f.write(wf_contents.encode('utf-8'))

    di_metadata_path = os.path.join(dist_info_path, 'METADATA')
    mf_contents = wheel.generate_metadata_file(
        name,
        version,
        description,
        url
    )
    with open(di_metadata_path, 'wb') as f:
        f.write(mf_contents.encode('utf-8'))

    di_installer_path = os.path.join(dist_info_path, 'INSTALLER')
    if_contents = wheel.generate_installer()
    with open(di_installer_path, 'wb') as f:
        f.write(if_contents.encode('utf-8'))

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

    di_record_path = os.path.join(dist_info_path, 'RECORD')
    # Create an empty file so it shows up in its own file list
    with open(di_record_path, 'wb') as f:
        f.write(b'')
    rf_contents = wheel.generate_record(
        dest_root,
        dist_info_dirname,
        package_dir_names,
        package_file_names
    )
    with open(di_record_path, 'wb') as f:
        f.write(rf_contents.encode('utf-8'))
