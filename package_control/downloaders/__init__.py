import os

if os.name == 'nt':
    from .wininet_downloader import WinINetDownloader
    DOWNLOADERS = [WinINetDownloader]

else:
    from .urllib_downloader import UrlLibDownloader
    from .curl_downloader import CurlDownloader
    from .wget_downloader import WgetDownloader
    DOWNLOADERS = [UrlLibDownloader, CurlDownloader, WgetDownloader]
