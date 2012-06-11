# -*- coding: utf-8 -*-

"""
requests.exceptions
~~~~~~~~~~~~~~~~~~~

This module contains the set of Requests' exceptions.

"""

class RequestException(RuntimeError):
    """There was an ambiguous exception that occurred while handling your
    request."""

class HTTPError(RequestException):
    """An HTTP error occurred."""
    response = None

class ConnectionError(RequestException):
    """A Connection error occurred."""

class SSLError(ConnectionError):
    """An SSL error occurred."""

class Timeout(RequestException):
    """The request timed out."""

class URLRequired(RequestException):
    """A valid URL is required to make a request."""

class TooManyRedirects(RequestException):
    """Too many redirects."""

class MissingSchema(RequestException, ValueError):
    """The URL schema (e.g. http or https) is missing."""

class InvalidSchema(RequestException, ValueError):
    """See defaults.py for valid schemas."""

class InvalidURL(RequestException, ValueError):
    """ The URL provided was somehow invalid. """
