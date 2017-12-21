
class NonHttpError(Exception):
    """A downloader had a non-clean exit, but not due to an HTTP error."""
    pass
