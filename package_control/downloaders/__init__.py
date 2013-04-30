import os

from .urllib_downloader import UrlLibDownloader
from .curl_downloader import CurlDownloader
from .wget_downloader import WgetDownloader
from .wininet_downloader import WinINetDownloader


if os.name == 'nt':
	DOWNLOADERS = [WinINetDownloader]
else:
	DOWNLOADERS = [UrlLibDownloader, CurlDownloader, WgetDownloader]
