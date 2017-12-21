import os

from .curl_downloader import CurlDownloader
from .urllib_downloader import UrlLibDownloader
from .wget_downloader import WgetDownloader

DOWNLOADERS = {
    'urllib': UrlLibDownloader,
    'curl': CurlDownloader,
    'wget': WgetDownloader
}

if os.name == 'nt':
    from .wininet_downloader import WinINetDownloader
    DOWNLOADERS['wininet'] = WinINetDownloader
