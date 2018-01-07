import os
import stat

from .console_write import console_write


def clean_old_files(directory):
    """
    Goes through a folder and removes all .package-control-old files
    that were created when PC ran into a locked file

    :param directory:
        The directory to clean
    """

    if not os.path.exists(os.path.join(directory, 'package-control.old')):
        return

    for root, dirs, files in os.walk(directory, topdown=False):
        for f in files:
            if f.endswith('.package-control-old'):
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                except (OSError) as e:
                    console_write(
                        '''
                        Error removing old file "%s": %s
                        ''',
                        (path, str(e))
                    )


def clear_directory(directory, ignore_paths=None):
    """
    Tries to delete all files and folders from a directory

    :param directory:
        The string directory path

    :param ignore_paths:
        An array of paths to ignore while deleting files

    :return:
        If all of the files and folders were successfully deleted
    """
    was_renamed = False
    was_exception = False
    for root, folders, files in os.walk(directory, topdown=False):
        for file in files:
            path = os.path.join(root, file)
            # Don't delete the metadata file, that way we have it
            # when the reinstall happens, and the appropriate
            # usage info can be sent back to the server
            if ignore_paths and path in ignore_paths:
                continue

            try:
                try:
                    os.remove(path)
                except PermissionError:
                    if os.name == 'nt':
                        os.chmod(path, stat.S_IWUSR)
                        os.remove(path)
                    else:
                        raise
            except IOError:
                was_exception = True
            except OSError:
                # try to rename file to reduce chance that
                # file is in use on next start
                if not path.endswith('.package-control-old'):
                    os.rename(path, path + '.package-control-old')
                    was_renamed = True
                was_exception = True

        for folder in folders:
            path = os.path.join(root, folder)
            # Don't delete the metadata file, that way we have it
            # when the reinstall happens, and the appropriate
            # usage info can be sent back to the server
            if ignore_paths and path in ignore_paths:
                continue

            try:
                os.rmdir(path)
            except (OSError, IOError):
                was_exception = True

    if was_renamed:
        # mark the directory for cleaning up old files
        open(os.path.join(directory, 'package-control.old'), 'wb').close()
    return not was_exception


def delete_directory(path):
    """
    Tries to delete a folder, changing files from read-only if such files
    are encountered

    :param path:
        The path to the folder to be deleted
    """
    if clear_directory(path):
        try:
            os.rmdir(path)
            return True
        except OSError:
            pass
    return False
