import os
import stat
import shutil
import sys
from .console_write import console_write
from .unicode import unicode_from_os


try:
    str_cls = unicode
except (NameError):
    str_cls = str


def is_directory_symlink(path):
    if sys.platform == 'win32':
        import ctypes

        if os.path.isdir(path):
            FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
            attributes = ctypes.windll.kernel32.GetFileAttributesW(str_cls(path))
            return (attributes & FILE_ATTRIBUTE_REPARSE_POINT) > 0
        return False
    else:
        return os.path.isdir(path) and os.path.islink(path)


def clean_old_files(directory):
    """
    Goes through a folder and removes all .package-control-old files
    that were created when PC ran into a locked file

    :param directory:
        The directory to clean
    """

    for root, dirs, files in os.walk(directory, topdown=False):
        for f in files:
            if f.endswith('.package-control-old'):
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                except (OSError) as e:
                    console_write(
                        u'''
                        Error removing old file "%s": %s
                        ''',
                        (path, unicode_from_os(e))
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

    was_exception = False
    for root, dirs, files in os.walk(directory, topdown=False):
        paths = [os.path.join(root, f) for f in files]
        paths.extend([os.path.join(root, d) for d in dirs])

        for path in paths:
            try:
                # Don't delete the metadata file, that way we have it
                # when the reinstall happens, and the appropriate
                # usage info can be sent back to the server
                if ignore_paths and path in ignore_paths:
                    continue
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    try:
                        if os.name == 'nt' and not os.access(path, os.W_OK):
                            try:
                                os.chmod(path, stat.S_IWUSR)
                            except EnvironmentError:
                                pass
                        os.remove(path)
                    except OSError:
                        # try to rename file to reduce chance that
                        # file is in use on next start
                        if not path.endswith('.package-control-old'):
                            os.rename(path, path + '.package-control-old')
                        raise
            except (OSError, IOError):
                was_exception = True

    return not was_exception


def _on_error(function, path, excinfo):
    """
    Error handler for shutil.rmtree that tries to add write privileges

    :param func:
        The function that raised the error

    :param path:
        The full filesystem path to the file

    :param excinfo:
        The exception information
    """

    try:
        if os.access(path, os.W_OK):
            raise OSError()
        os.chmod(path, stat.S_IWUSR)
        function(path)
    except (OSError):
        # Try to rename file to reduce chance that file is in use on next
        # start. However, if an error occurs with the rename, just ignore it
        # so that we can continue removing other files. Hopefully this should
        # result in a folder with just a .dll file in it after restart, which
        # should clean up no problem. Without catching the OSError here, the
        # python file that imports the .dll may never get deleted, meaning that
        # the package can never be cleanly removed.
        try:
            if not os.path.isdir(path) and not path.endswith('.package-control-old'):
                os.rename(path, path + '.package-control-old')
        except (OSError):
            pass


def unlink_or_delete_directory(path):
    """
    Tries to delete a folder, changing files from read-only if such files
    are encountered. If a folder is a symlink, the symlink will be removed and not
    the contents of symlinked folder.

    :param path:
        The path to the folder to be deleted or unlinked
    """

    if is_directory_symlink(path):
        try:
            if sys.platform == 'win32':
                os.rmdir(path)
            else:
                os.unlink(path)
            return True
        except OSError:
            # Fall back to non-symlink handling
            pass

    shutil.rmtree(path, onerror=_on_error)
    return not os.path.exists(path)
