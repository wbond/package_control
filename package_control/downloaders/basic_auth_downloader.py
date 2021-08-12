import base64

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse


class BasicAuthDownloader(object):

    """
    A base for downloaders to add an HTTP basic auth header
    """

    def build_auth_header(self, url):
        """
        Constructs an HTTP basic auth header for a URL, if present in
        settings

        :param url:
            A unicode string of the URL being downloaded

        :return:
            A dict with an HTTP header name as the key and the value as the
            value. Both are unicode strings.
        """

        auth_string = self.get_auth_string(url)
        if not auth_string:
            return {}
        b64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        return {"Authorization": "Basic %s" % b64_auth}

    def get_auth_string(self, url):
        """
        Constructs a string of username:password for use in HTTP basic auth

        :param url:
            A unicode string of the URL being downloaded

        :return:
            None, or a unicode string of the username:password for the URL
        """

        username, password = self.get_username_password(url)
        if username and password:
            return "%s:%s" % (username, password)
        return None

    def get_username_password(self, url):
        """
        Returns a tuple of (username, password) for use in HTTP basic auth

        :param url:
            A unicode string of the URL being downloaded

        :return:
            A 2-element tuple of either (None, None) or (username, password)
            as unicode strings
        """

        domain_name = urlparse(url).netloc

        auth_settings = self.settings.get('http_basic_auth')
        domain_name = urlparse(url).netloc
        if auth_settings and isinstance(auth_settings, dict):
            params = auth_settings.get(domain_name)
            if params and isinstance(params, (list, tuple)) and len(params) == 2:
                return (params[0], params[1])
        return (None, None)
