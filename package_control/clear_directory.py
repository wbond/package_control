import os
import stat
import sys

from . import sys_path

IS_WIN = sys.platform == 'win32'
if IS_WIN:
    import ctypes


def is_symlink(path):
    if IS_WIN:
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return (attributes & FILE_ATTRIBUTE_REPARSE_POINT) > 0

    return os.path.islink(path)


def clear_directory(directory, ignored_files=None):
    """
    Tries to delete all files and folders from a directory

    :param directory:
        The normalized absolute path to the folder to be cleared

    :param ignored_files:
        An set of paths to ignore while deleting files

    :return:
        If all of the files and folders were successfully deleted
    """

    # make sure not to lock directory by current working directory
    if sys_path.longpath(os.path.normcase(os.getcwd())).startswith(os.path.normcase(directory)):
        os.chdir(os.path.dirname(directory))

    was_exception = False
    for root, dirs, files in os.walk(directory, topdown=False):
        try:
            for d in dirs:
                os.rmdir(os.path.join(root, d))

            for f in files:
                path = os.path.join(root, f)
                # Don't delete the metadata file, that way we have it
                # when the reinstall happens, and the appropriate
                # usage info can be sent back to the server
                if ignored_files and path in ignored_files:
                    continue

                try:
                    if IS_WIN and not os.access(path, os.W_OK):
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


def delete_directory(directory):
    """
    Clear and delete a directory tree beginning with the deepest nested files.

    This is to work around a file lock issues with ST's git library on Windows,
    which causes OSError 5 or 123 when using ``shutil.rmtree()``.

        see: https://github.com/sublimehq/sublime_text/issues/3124

    Tries to achieve write access for any encountered read-only file.

    If the folder is a symlink, the symlink is removed and not the contents
    of symlinked folder.

    :noted:
        1. Implementation uses python 3.3 compatible ``is_symlink()`` function.
        2. It is not expected to find symlinked sub-directories.

    :param directory:
        The normalized absolute path to the folder to be deleted or unlinked
    """

    if os.path.isdir(directory):
        if is_symlink(directory):
            try:
                if IS_WIN:
                    os.rmdir(directory)
                else:
                    os.unlink(directory)
                return True
            except OSError:
                pass

        elif clear_directory(directory):
            try:
                os.rmdir(directory)
                return True
            except OSError:
                pass

    return False
