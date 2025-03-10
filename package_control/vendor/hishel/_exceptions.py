__all__ = ("CacheControlError", "ParseError", "ValidationError")


class CacheControlError(Exception): ...


class ParseError(CacheControlError): ...


class ValidationError(CacheControlError): ...
