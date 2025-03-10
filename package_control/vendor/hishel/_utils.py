import calendar
import time
import typing as tp
from email.utils import parsedate_tz
from hashlib import blake2b

from .. import anyio
from .. import httpcore
from .. import httpx

HEADERS_ENCODING = "iso-8859-1"


class BaseClock:
    def now(self) -> int:
        raise NotImplementedError()


class Clock(BaseClock):
    def now(self) -> int:
        return int(time.time())


def normalized_url(url: tp.Union[httpcore.URL, str, bytes]) -> str:
    if isinstance(url, str):  # pragma: no cover
        return url

    if isinstance(url, bytes):  # pragma: no cover
        return url.decode("ascii")

    if isinstance(url, httpcore.URL):
        port = f":{url.port}" if url.port is not None else ""
        return f'{url.scheme.decode("ascii")}://{url.host.decode("ascii")}{port}{url.target.decode("ascii")}'
    assert False, "Invalid type for `normalized_url`"  # pragma: no cover


def get_safe_url(url: httpcore.URL) -> str:
    httpx_url = httpx.URL(bytes(url).decode("ascii"))

    schema = httpx_url.scheme
    host = httpx_url.host
    path = httpx_url.path

    return f"{schema}://{host}{path}"


def generate_key(request: httpcore.Request, body: bytes = b"") -> str:
    encoded_url = normalized_url(request.url).encode("ascii")

    key_parts = [request.method, encoded_url, body]

    key = blake2b(digest_size=16)
    for part in key_parts:
        key.update(part)
    return key.hexdigest()


def extract_header_values(
    headers: tp.List[tp.Tuple[bytes, bytes]],
    header_key: tp.Union[bytes, str],
    single: bool = False,
) -> tp.List[bytes]:
    if isinstance(header_key, str):
        header_key = header_key.encode(HEADERS_ENCODING)
    extracted_headers = []
    for key, value in headers:
        if key.lower() == header_key.lower():
            extracted_headers.append(value)
            if single:
                break
    return extracted_headers


def extract_header_values_decoded(
    headers: tp.List[tp.Tuple[bytes, bytes]], header_key: bytes, single: bool = False
) -> tp.List[str]:
    values = extract_header_values(headers=headers, header_key=header_key, single=single)
    return [value.decode(HEADERS_ENCODING) for value in values]


def header_presents(headers: tp.List[tp.Tuple[bytes, bytes]], header_key: bytes) -> bool:
    return bool(extract_header_values(headers, header_key, single=True))


def parse_date(date: str) -> int:
    expires = parsedate_tz(date)
    timestamp = calendar.timegm(expires[:6])  # type: ignore
    return timestamp


async def asleep(seconds: tp.Union[int, float]) -> None:
    await anyio.sleep(seconds)


def sleep(seconds: tp.Union[int, float]) -> None:
    time.sleep(seconds)


def float_seconds_to_int_milliseconds(seconds: float) -> int:
    return int(seconds * 1000)
