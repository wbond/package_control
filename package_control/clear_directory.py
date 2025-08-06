import errno
import os
import stat
import sys

from datetime import datetime
from hashlib import sha1

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


def clear_directory(directory, ignored_files=None, ignore_errors=True):
    """
    Tries to delete all files and folders from a directory

    :param directory:
        The normalized absolute path to the folder to be cleared

    :param ignored_files:
        An set of paths to ignore while deleting files

    :param ignore_errors:
        If ``True`` don't raise exceptions if intermediate operation fails,
        just return boolean result after all.

    :return:
        If all of the files and folders were successfully deleted
    """

    if not os.path.isdir(directory):
        return True

    # make sure not to lock directory by current working directory
    if sys_path.longpath(os.path.normcase(os.getcwd())).startswith(os.path.normcase(directory)):
        os.chdir(os.path.dirname(directory))

    # use timestamp as session id, in case library is installed/removed
    # multiple times to avoid naming conflicts, when moving to trash.
    session_id = str(datetime.now())

    # Especially on Windows, files may be locked and therefore can't be removed,
    # while loaded. They can however be renamed, thus moving them to trash directory is
    # possible in order to simulate deletion for the sense of managing packages/libraries.
    trash_dir = sys_path.trash_path()
    os.makedirs(trash_dir, exist_ok=True)

    was_exception = False

    for root, dirs, files in os.walk(directory, topdown=False):
        try:
            for f in files:
                path = os.path.normcase(os.path.join(root, f))
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
                    trash_path = os.path.join(
                        trash_dir,
                        sha1((session_id + path).encode('utf-8')).hexdigest().lower()
                    )
                    os.rename(path, trash_path)

            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError as e:
                    if e.errno == errno.ENOTEMPTY:
                        continue
                    raise

        except OSError:
            if not ignore_errors:
                raise
            was_exception = True

    return not was_exception


def delete_directory(directory, ignore_errors=True):
    """
    Clear and delete a directory tree beginning with the deepest nested files.

    This is to work around a file lock issues with ST's git library on Windows,
    which causes OSError 5 or 123 when using ``shutil.rmtree()``.

        see: https://github.com/sublimehq/sublime_text/issues/3124

    Tries to achieve write access for any encountered read-only file.

    If the folder is a symlink, the symlink is removed and not the contents
    of symlinked folder.

    If a file can't be removed due to being locked, it is moved to trash folder,
    which is located in ST's data directory ``$DATA/Trash``.

    :note:
        1. Implementation uses python 3.3 compatible ``is_symlink()`` function.
        2. It is not expected to find symlinked sub-directories.

    :param directory:
        The normalized absolute path to the folder to be deleted or unlinked

    :param ignore_errors:
        If ``True`` don't raise exceptions if intermediate operation fails,
        just return boolean result after all.
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
                if not ignore_errors:
                    raise

        elif clear_directory(directory, ignore_errors=ignore_errors):
            try:
                os.rmdir(directory)
                return True
            except OSError:
                if not ignore_errors:
                    raise

    return False
