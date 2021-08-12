import sys

from .urllib_downloader import UrlLibDownloader
from .curl_downloader import CurlDownloader
from .wget_downloader import WgetDownloader

DOWNLOADERS = {
    'urllib': UrlLibDownloader,
    'curl': CurlDownloader,
    'wget': WgetDownloader
}

# oscrypto can fail badly on Linux in the Sublime Text 3 environment due to
# trying to mix the statically-linked OpenSSL in plugin_host with the OpenSSL
# loaded from the operating system. On Python 3.8 we dynamically link OpenSSL,
# so it just needs to be configured properly, which is handled in
# oscrypto_downloader.py.
if sys.platform != 'linux' or sys.version_info[:2] != (3, 3) or \
        sys.executable != 'python3':
    from .oscrypto_downloader import OscryptoDownloader
    DOWNLOADERS['oscrypto'] = OscryptoDownloader

if sys.platform == 'win32':
    from .wininet_downloader import WinINetDownloader
    DOWNLOADERS['wininet'] = WinINetDownloader
