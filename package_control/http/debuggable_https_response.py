from .debuggable_http_response import DebuggableHTTPResponse


class DebuggableHTTPSResponse(DebuggableHTTPResponse):
    """
    A version of DebuggableHTTPResponse that sets the debug protocol to HTTPS
    """

    _debug_protocol = 'HTTPS'
