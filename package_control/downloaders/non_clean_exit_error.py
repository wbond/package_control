import sys

try:
    # Python 2
    str_cls = unicode
except (NameError):
    # Python 3
    str_cls = str


class NonCleanExitError(Exception):

    """
    When an subprocess does not exit cleanly

    :param returncode:
        The command line integer return code of the subprocess
    """

    def __init__(self, returncode):
        self.returncode = returncode

    def __unicode__(self):
        return str_cls(self.returncode)

    def __str__(self):
        if sys.version_info < (3,):
            return self.__bytes__()
        return self.__unicode__()

    def __bytes__(self):
        return self.__unicode__().encode('utf-8')
