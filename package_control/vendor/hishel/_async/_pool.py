from __future__ import annotations

import types
import typing as tp

from ...httpcore._async.interfaces import AsyncRequestInterface
from ...httpcore._exceptions import ConnectError
from ...httpcore._models import Request, Response

from .._controller import Controller, allowed_stale
from .._headers import parse_cache_control
from .._serializers import JSONSerializer, Metadata
from .._utils import extract_header_values_decoded
from ._storages import AsyncBaseStorage, AsyncFileStorage

T = tp.TypeVar("T")

__all__ = ("AsyncCacheConnectionPool",)


async def fake_stream(content: bytes) -> tp.AsyncIterable[bytes]:
    yield content


def generate_504() -> Response:
    return Response(status=504)


class AsyncCacheConnectionPool(AsyncRequestInterface):
    """An HTTP Core Connection Pool that supports HTTP caching.

    :param pool: `Connection Pool` that our class wraps in order to add an HTTP Cache layer on top of
    :type pool: AsyncRequestInterface
    :param storage: Storage that handles how the responses should be saved., defaults to None
    :type storage: tp.Optional[AsyncBaseStorage], optional
    :param controller: Controller that manages the cache behavior at the specification level, defaults to None
    :type controller: tp.Optional[Controller], optional
    """

    def __init__(
        self,
        pool: AsyncRequestInterface,
        storage: tp.Optional[AsyncBaseStorage] = None,
        controller: tp.Optional[Controller] = None,
    ) -> None:
        self._pool = pool

        self._storage = storage if storage is not None else AsyncFileStorage(serializer=JSONSerializer())

        if not isinstance(self._storage, AsyncBaseStorage):
            raise TypeError(f"Expected subclass of `AsyncBaseStorage` but got `{storage.__class__.__name__}`")

        self._controller = controller if controller is not None else Controller()

    async def handle_async_request(self, request: Request) -> Response:
        """
        Handles HTTP requests while also implementing HTTP caching.

        :param request: An HTTP request
        :type request: httpcore.Request
        :return: An HTTP response
        :rtype: httpcore.Response
        """

        if request.extensions.get("cache_disabled", False):
            request.headers.extend([(b"cache-control", b"no-cache"), (b"cache-control", b"max-age=0")])

        if request.method.upper() not in [b"GET", b"HEAD"]:
            # If the HTTP method is, for example, POST,
            # we must also use the request data to generate the hash.
            assert isinstance(request.stream, tp.AsyncIterable)
            body_for_key = b"".join([chunk async for chunk in request.stream])
            request.stream = fake_stream(body_for_key)
        else:
            body_for_key = b""

        key = self._controller._key_generator(request, body_for_key)
        stored_data = await self._storage.retrieve(key)

        request_cache_control = parse_cache_control(extract_header_values_decoded(request.headers, b"Cache-Control"))

        if request_cache_control.only_if_cached and not stored_data:
            return generate_504()

        if stored_data:
            # Try using the stored response if it was discovered.

            stored_response, stored_request, metadata = stored_data

            # Immediately read the stored response to avoid issues when trying to access the response body.
            stored_response.read()

            res = self._controller.construct_response_from_cache(
                request=request,
                response=stored_response,
                original_request=stored_request,
            )

            if isinstance(res, Response):
                # Simply use the response if the controller determines it is ready for use.
                return await self._create_hishel_response(
                    key=key,
                    response=stored_response,
                    request=request,
                    metadata=metadata,
                    cached=True,
                    revalidated=False,
                )

            if request_cache_control.only_if_cached:
                return generate_504()

            if isinstance(res, Request):
                # Controller has determined that the response needs to be re-validated.

                try:
                    revalidation_response = await self._pool.handle_async_request(res)
                except ConnectError:
                    # If there is a connection error, we can use the stale response if allowed.
                    if self._controller._allow_stale and allowed_stale(response=stored_response):
                        return await self._create_hishel_response(
                            key=key,
                            response=stored_response,
                            request=request,
                            metadata=metadata,
                            cached=True,
                            revalidated=False,
                        )
                    raise  # pragma: no cover
                # Merge headers with the stale response.
                final_response = self._controller.handle_validation_response(
                    old_response=stored_response, new_response=revalidation_response
                )

                await final_response.aread()

                # RFC 9111: 4.3.3. Handling a Validation Response
                # A 304 (Not Modified) response status code indicates that the stored response can be updated and
                # reused. A full response (i.e., one containing content) indicates that none of the stored responses
                # nominated in the conditional request are suitable. Instead, the cache MUST use the full response to
                # satisfy the request. The cache MAY store such a full response, subject to its constraints.
                if revalidation_response.status != 304 and self._controller.is_cachable(
                    request=request, response=final_response
                ):
                    await self._storage.store(key, response=final_response, request=request)

                return await self._create_hishel_response(
                    key=key,
                    response=final_response,
                    request=request,
                    cached=revalidation_response.status == 304,
                    revalidated=True,
                    metadata=metadata,
                )

        regular_response = await self._pool.handle_async_request(request)
        await regular_response.aread()

        if self._controller.is_cachable(request=request, response=regular_response):
            await self._storage.store(key, response=regular_response, request=request)

        return await self._create_hishel_response(
            key=key, response=regular_response, request=request, cached=False, revalidated=False
        )

    async def _create_hishel_response(
        self,
        key: str,
        response: Response,
        request: Request,
        cached: bool,
        revalidated: bool,
        metadata: Metadata | None = None,
    ) -> Response:
        if cached:
            assert metadata
            metadata["number_of_uses"] += 1
            await self._storage.update_metadata(key=key, request=request, response=response, metadata=metadata)
            response.extensions["from_cache"] = True  # type: ignore[index]
            response.extensions["cache_metadata"] = metadata  # type: ignore[index]
        else:
            response.extensions["from_cache"] = False  # type: ignore[index]
        response.extensions["revalidated"] = revalidated  # type: ignore[index]
        return response

    async def aclose(self) -> None:
        await self._storage.aclose()

        if hasattr(self._pool, "aclose"):  # pragma: no cover
            await self._pool.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(
        self,
        exc_type: tp.Optional[tp.Type[BaseException]] = None,
        exc_value: tp.Optional[BaseException] = None,
        traceback: tp.Optional[types.TracebackType] = None,
    ) -> None:
        await self.aclose()
