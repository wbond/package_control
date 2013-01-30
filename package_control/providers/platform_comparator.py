import sublime


class PlatformComparator():
    """
    A base class for finding the best version of a package for the current machine
    """

    def get_best_platform(self, platforms):
        """
        Returns the most specific platform that matches the current machine

        :param platforms:
            An array of platform names for a package. E.g. ['*', 'windows', 'linux-x64']

        :return: A string reprenting the most specific matching platform
        """

        ids = [sublime.platform() + '-' + sublime.arch(), sublime.platform(),
            '*']

        for id in ids:
            if id in platforms:
                return id

        return None
