import os


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
                    os.remove(path)
            except (OSError, IOError):
                was_exception = True

    return not was_exception
