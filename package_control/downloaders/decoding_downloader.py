import gzip
import zlib

try:
    # Python 3
    from io import BytesIO as StringIO
except (ImportError):
    # Python 2
    from StringIO import StringIO

try:
    import bz2
except (ImportError):
    bz2 = None

from .downloader_exception import DownloaderException


class DecodingDownloader(object):
    """
    A base for downloaders that provides the ability to decode bzip2ed, gzipped
    or deflated content.
    """

    def supported_encodings(self):
        """
        Determines the supported encodings we can decode

        :return:
            A comma-separated string of valid encodings
        """

        encodings = 'gzip,deflate'
        if bz2:
            encodings = 'bzip2,' + encodings
        return encodings

    def decode_response(self, encoding, response):
        """
        Decodes the raw response from the web server based on the
        Content-Encoding HTTP header

        :param encoding:
            The value of the Content-Encoding HTTP header

        :param response:
            The raw response from the server

        :return:
            The decoded response
        """

        if encoding == 'bzip2':
            if bz2:
                return bz2.decompress(response)
            else:
                raise DownloaderException(u'Received bzip2 file contents, but was unable to import the bz2 module')
        elif encoding == 'gzip':
            return gzip.GzipFile(fileobj=StringIO(response)).read()
        elif encoding == 'deflate':
            decompresser = zlib.decompressobj(-zlib.MAX_WBITS)
            return decompresser.decompress(response) + decompresser.flush()
        return response
