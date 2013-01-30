class NonHttpError(Exception):
    """If a downloader had a non-clean exit, but it was not due to an HTTP error"""

    pass
