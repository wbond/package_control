import os
import shutil
import stat



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
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        function(path)
    else:
        raise


def rmtree(path):
    """
    Tries to delete a folder, changing files from read-only if such files
    are encountered

    :param path:
        The path to the folder to be deleted
    """
    shutil.rmtree(path, onerror=_on_error)
