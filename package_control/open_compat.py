import os

from .file_not_found_error import FileNotFoundError


def open_compat(path, mode='r'):
    if mode in ['r', 'rb'] and not os.path.exists(path):
        raise FileNotFoundError(u"The file \"%s\" could not be found" % path)

    encoding = 'utf-8'
    errors = 'replace'
    if mode in ['rb', 'wb', 'ab']:
        encoding = None
        errors = None
    return open(path, mode, encoding=encoding, errors=errors)


def read_compat(file_obj):
    return file_obj.read()


def write_compat(file_obj, value):
    return file_obj.write(str(value))
