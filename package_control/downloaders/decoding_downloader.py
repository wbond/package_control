import gzip
import zlib

try:
    # Python 3
    from io import BytesIO as StringIO
except (ImportError):
    # Python 2
    from StringIO import StringIO


class DecodingDownloader(object):
    """
    A base for downloaders that provides the ability to decode gzipped
    or deflated content.
    """

    def decode_response(self, encoding, response):
        if encoding == 'gzip':
            return gzip.GzipFile(fileobj=StringIO(response)).read()
        elif encoding == 'deflate':
            decompresser = zlib.decompressobj(-zlib.MAX_WBITS)
            return decompresser.decompress(response) + decompresser.flush()
        return response
