class NonHttpError(Exception):
    """If a downloader had a non-clean exit, but it was not due to an HTTP error"""

    def __str__(self):
        return self.args[0]
