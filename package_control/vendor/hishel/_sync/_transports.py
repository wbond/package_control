from __future__ import annotations

import types
import typing as tp

from ... import httpcore
from ... import httpx
from ...httpx import ByteStream, Request, Response
from ...httpx._exceptions import ConnectError

from ...hishel._utils import extract_header_values_decoded, normalized_url

from .._controller import Controller, allowed_stale
from .._headers import parse_cache_control
from .._serializers import JSONSerializer, Metadata
from ._storages import BaseStorage, FileStorage

if tp.TYPE_CHECKING:  # pragma: no cover
    from ...typing_extensions import Self

__all__ = ("CacheTransport",)


def fake_stream(content: bytes) -> tp.Iterable[bytes]:
    yield content


def generate_504() -> Response:
    return Response(status_code=504)


class CacheStream(ByteStream):
    def __init__(self, httpcore_stream: tp.Iterable[bytes]):
        self._httpcore_stream = httpcore_stream

    def __iter__(self) -> tp.Iterator[bytes]:
        for part in self._httpcore_stream:
            yield part

    def close(self) -> None:
        if hasattr(self._httpcore_stream, "close"):
            self._httpcore_stream.close()


class CacheTransport(httpx.BaseTransport):
    """
    An HTTPX Transport that supports HTTP caching.

    :param transport: `Transport` that our class wraps in order to add an HTTP Cache layer on top of
    :type transport: httpx.BaseTransport
    :param storage: Storage that handles how the responses should be saved., defaults to None
    :type storage: tp.Optional[BaseStorage], optional
    :param controller: Controller that manages the cache behavior at the specification level, defaults to None
    :type controller: tp.Optional[Controller], optional
    """

    def __init__(
        self,
        transport: httpx.BaseTransport,
        storage: tp.Optional[BaseStorage] = None,
        controller: tp.Optional[Controller] = None,
    ) -> None:
        self._transport = transport

        self._storage = storage if storage is not None else FileStorage(serializer=JSONSerializer())

        if not isinstance(self._storage, BaseStorage):
            raise TypeError(f"Expected subclass of `BaseStorage` but got `{storage.__class__.__name__}`")

        self._controller = controller if controller is not None else Controller()

    def handle_request(self, request: Request) -> Response:
        """
        Handles HTTP requests while also implementing HTTP caching.

        :param request: An HTTP request
        :type request: httpx.Request
        :return: An HTTP response
        :rtype: httpx.Response
        """

        if request.extensions.get("cache_disabled", False):
            request.headers.update(
                [
                    ("Cache-Control", "no-store"),
                    ("Cache-Control", "no-cache"),
                    *[("cache-control", value) for value in request.headers.get_list("cache-control")],
                ]
            )

        if request.method not in ["GET", "HEAD"]:
            # If the HTTP method is, for example, POST,
            # we must also use the request data to generate the hash.
            body_for_key = request.read()
            request.stream = CacheStream(fake_stream(body_for_key))
        else:
            body_for_key = b""

        # Construct the HTTPCore request because Controllers and Storages work with HTTPCore requests.
        httpcore_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )

        key = self._controller._key_generator(httpcore_request, body_for_key)
        stored_data = self._storage.retrieve(key)

        request_cache_control = parse_cache_control(
            extract_header_values_decoded(request.headers.raw, b"Cache-Control")
        )

        if request_cache_control.only_if_cached and not stored_data:
            return generate_504()

        if stored_data:
            # Try using the stored response if it was discovered.

            stored_response, stored_request, metadata = stored_data

            # Immediately read the stored response to avoid issues when trying to access the response body.
            stored_response.read()

            res = self._controller.construct_response_from_cache(
                request=httpcore_request,
                response=stored_response,
                original_request=stored_request,
            )

            if isinstance(res, httpcore.Response):
                # Simply use the response if the controller determines it is ready for use.
                return self._create_hishel_response(
                    key=key,
                    response=res,
                    request=httpcore_request,
                    cached=True,
                    revalidated=False,
                    metadata=metadata,
                )

            if request_cache_control.only_if_cached:
                return generate_504()

            if isinstance(res, httpcore.Request):
                # Controller has determined that the response needs to be re-validated.
                assert isinstance(res.stream, tp.Iterable)
                revalidation_request = Request(
                    method=res.method,
                    url=normalized_url(res.url),
                    headers=res.headers,
                    stream=CacheStream(res.stream),
                    extensions=res.extensions,
                )
                try:
                    revalidation_response = self._transport.handle_request(revalidation_request)
                except ConnectError:
                    # If there is a connection error, we can use the stale response if allowed.
                    if self._controller._allow_stale and allowed_stale(response=stored_response):
                        return self._create_hishel_response(
                            key=key,
                            response=stored_response,
                            request=httpcore_request,
                            cached=True,
                            revalidated=False,
                            metadata=metadata,
                        )
                    raise  # pragma: no cover
                assert isinstance(revalidation_response.stream, tp.Iterable)
                httpcore_revalidation_response = httpcore.Response(
                    status=revalidation_response.status_code,
                    headers=revalidation_response.headers.raw,
                    content=CacheStream(revalidation_response.stream),
                    extensions=revalidation_response.extensions,
                )

                # Merge headers with the stale response.
                final_httpcore_response = self._controller.handle_validation_response(
                    old_response=stored_response,
                    new_response=httpcore_revalidation_response,
                )

                final_httpcore_response.read()
                revalidation_response.close()

                assert isinstance(final_httpcore_response.stream, tp.Iterable)

                # RFC 9111: 4.3.3. Handling a Validation Response
                # A 304 (Not Modified) response status code indicates that the stored response can be updated and
                # reused. A full response (i.e., one containing content) indicates that none of the stored responses
                # nominated in the conditional request are suitable. Instead, the cache MUST use the full response to
                # satisfy the request. The cache MAY store such a full response, subject to its constraints.
                if revalidation_response.status_code != 304 and self._controller.is_cachable(
                    request=httpcore_request, response=final_httpcore_response
                ):
                    self._storage.store(key, response=final_httpcore_response, request=httpcore_request)

                return self._create_hishel_response(
                    key=key,
                    response=final_httpcore_response,
                    request=httpcore_request,
                    cached=revalidation_response.status_code == 304,
                    revalidated=True,
                    metadata=metadata,
                )

        regular_response = self._transport.handle_request(request)
        assert isinstance(regular_response.stream, tp.Iterable)
        httpcore_regular_response = httpcore.Response(
            status=regular_response.status_code,
            headers=regular_response.headers.raw,
            content=CacheStream(regular_response.stream),
            extensions=regular_response.extensions,
        )
        httpcore_regular_response.read()
        httpcore_regular_response.close()

        if self._controller.is_cachable(request=httpcore_request, response=httpcore_regular_response):
            self._storage.store(
                key,
                response=httpcore_regular_response,
                request=httpcore_request,
            )

        return self._create_hishel_response(
            key=key,
            response=httpcore_regular_response,
            request=httpcore_request,
            cached=False,
            revalidated=False,
        )

    def _create_hishel_response(
        self,
        key: str,
        response: httpcore.Response,
        request: httpcore.Request,
        cached: bool,
        revalidated: bool,
        metadata: Metadata | None = None,
    ) -> Response:
        if cached:
            assert metadata
            metadata["number_of_uses"] += 1
            self._storage.update_metadata(key=key, request=request, response=response, metadata=metadata)
            response.extensions["from_cache"] = True  # type: ignore[index]
            response.extensions["cache_metadata"] = metadata  # type: ignore[index]
        else:
            response.extensions["from_cache"] = False  # type: ignore[index]
        response.extensions["revalidated"] = revalidated  # type: ignore[index]
        return Response(
            status_code=response.status,
            headers=response.headers,
            stream=CacheStream(fake_stream(response.content)),
            extensions=response.extensions,
        )

    def close(self) -> None:
        self._storage.close()
        self._transport.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: tp.Optional[tp.Type[BaseException]] = None,
        exc_value: tp.Optional[BaseException] = None,
        traceback: tp.Optional[types.TracebackType] = None,
    ) -> None:
        self.close()
