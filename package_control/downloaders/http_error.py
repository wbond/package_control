class HttpError(Exception):
    """If a downloader was able to download a URL, but the result was not a 200 or 304"""

    def __init__(self, message, code):
        self.code = code
        super(HttpError, self).__init__(message)

    def __str__(self):
        return self.args[0]
