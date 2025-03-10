import logging
import typing as tp

from ..httpcore import Request, Response

from ..hishel._headers import Vary, parse_cache_control

from ._utils import (
    BaseClock,
    Clock,
    extract_header_values,
    extract_header_values_decoded,
    generate_key,
    get_safe_url,
    header_presents,
    parse_date,
)

logger = logging.getLogger("hishel.controller")

HEURISTICALLY_CACHEABLE_STATUS_CODES = (200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, 501)
HTTP_METHODS = ["GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"]

__all__ = ("Controller", "HEURISTICALLY_CACHEABLE_STATUS_CODES")


def get_updated_headers(
    stored_response_headers: tp.List[tp.Tuple[bytes, bytes]],
    new_response_headers: tp.List[tp.Tuple[bytes, bytes]],
) -> tp.List[tp.Tuple[bytes, bytes]]:
    updated_headers = []

    checked = set()

    for key, value in stored_response_headers:
        if key not in checked and key.lower() != b"content-length":
            checked.add(key)
            values = extract_header_values(new_response_headers, key)

            if values:
                updated_headers.extend([(key, value) for value in values])
            else:
                values = extract_header_values(stored_response_headers, key)
                updated_headers.extend([(key, value) for value in values])

    for key, value in new_response_headers:
        if key not in checked and key.lower() != b"content-length":
            values = extract_header_values(new_response_headers, key)
            updated_headers.extend([(key, value) for value in values])

    return updated_headers


def get_freshness_lifetime(response: Response) -> tp.Optional[int]:
    response_cache_control = parse_cache_control(extract_header_values_decoded(response.headers, b"Cache-Control"))

    if response_cache_control.max_age is not None:
        return response_cache_control.max_age

    if header_presents(response.headers, b"expires"):
        expires = extract_header_values_decoded(response.headers, b"expires", single=True)[0]
        expires_timestamp = parse_date(expires)
        date = extract_header_values_decoded(response.headers, b"date", single=True)[0]
        date_timestamp = parse_date(date)

        return expires_timestamp - date_timestamp
    return None


def get_heuristic_freshness(response: Response, clock: "BaseClock") -> int:
    last_modified = extract_header_values_decoded(response.headers, b"last-modified", single=True)

    if last_modified:
        last_modified_timestamp = parse_date(last_modified[0])
        now = clock.now()

        ONE_WEEK = 604_800

        return min(ONE_WEEK, int((now - last_modified_timestamp) * 0.1))

    ONE_DAY = 86_400
    return ONE_DAY


def get_age(response: Response, clock: "BaseClock") -> int:
    if not header_presents(response.headers, b"date"):
        # If the response does not have a date header, then it is impossible to calculate the age.
        # Instead of raising an exception, we return infinity to be sure that the response is not considered fresh.
        return float("inf")  # type: ignore

    date = parse_date(extract_header_values_decoded(response.headers, b"date")[0])

    now = clock.now()

    apparent_age = max(0, now - date)
    return int(apparent_age)


def allowed_stale(response: Response) -> bool:
    response_cache_control = parse_cache_control(extract_header_values_decoded(response.headers, b"Cache-Control"))

    if response_cache_control.no_cache:
        return False

    if response_cache_control.must_revalidate:
        return False

    return True


class Controller:
    def __init__(
        self,
        cacheable_methods: tp.Optional[tp.List[str]] = None,
        cacheable_status_codes: tp.Optional[tp.List[int]] = None,
        cache_private: bool = True,
        allow_heuristics: bool = False,
        clock: tp.Optional[BaseClock] = None,
        allow_stale: bool = False,
        always_revalidate: bool = False,
        force_cache: bool = False,
        key_generator: tp.Optional[tp.Callable[[Request, tp.Optional[bytes]], str]] = None,
    ):
        self._cacheable_methods = []

        if cacheable_methods is None:
            self._cacheable_methods.append("GET")
        else:
            for method in cacheable_methods:
                if method.upper() not in HTTP_METHODS:
                    raise RuntimeError(
                        f"Hishel does not support the HTTP method `{method}`.\n"
                        f"Please use the methods from this list: {HTTP_METHODS}"
                    )
                self._cacheable_methods.append(method.upper())

        self._cacheable_status_codes = cacheable_status_codes if cacheable_status_codes else [200, 301, 308]
        self._cache_private = cache_private
        self._clock = clock if clock else Clock()
        self._allow_heuristics = allow_heuristics
        self._allow_stale = allow_stale
        self._always_revalidate = always_revalidate
        self._force_cache = force_cache
        self._key_generator = key_generator or generate_key

    def is_cachable(self, request: Request, response: Response) -> bool:
        """
        Determines whether the response may be cached.

        The only thing this method does is determine whether the
        response associated with this request can be cached for later use.
        `https://www.rfc-editor.org/rfc/rfc9111.html#name-storing-responses-in-caches`
        lists the steps that this method simply follows.
        """
        method = request.method.decode("ascii")
        force_cache = request.extensions.get("force_cache", None)

        if response.status not in self._cacheable_status_codes:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    f"as not cachable since its status code ({response.status})"
                    " is not in the list of cacheable status codes."
                )
            )
            return False

        if response.status in (301, 308):
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as cachable since its status code is a permanent redirect."
                )
            )
            return True

        # the request method is understood by the cache
        if method not in self._cacheable_methods:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    f"as not cachable since the request method ({method}) is not in the list of cacheable methods."
                )
            )
            return False

        if force_cache if force_cache is not None else self._force_cache:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as cachable since the request is forced to use the cache."
                )
            )
            return True

        response_cache_control = parse_cache_control(extract_header_values_decoded(response.headers, b"cache-control"))
        request_cache_control = parse_cache_control(extract_header_values_decoded(request.headers, b"cache-control"))

        # the response status code is final
        if response.status // 100 == 1:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as not cachable since its status code is informational."
                )
            )
            return False

        # the no-store cache directive is not present (see Section 5.2.2.5)
        if request_cache_control.no_store:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as not cachable since the request contains the no-store directive."
                )
            )
            return False

        # note that the must-understand cache directive overrides
        # no-store in certain circumstances; see Section 5.2.2.3.
        if response_cache_control.no_store:
            if response_cache_control.must_understand:
                logger.debug(
                    (
                        f"Skipping the no-store directive for the resource located at {get_safe_url(request.url)} "
                        "since the response contains the must-understand directive."
                    )
                )
            else:
                logger.debug(
                    (
                        f"Considering the resource located at {get_safe_url(request.url)} "
                        "as not cachable since the response contains the no-store directive."
                    )
                )
                return False

        # a shared cache must not store a response with private directive
        # Note that we do not implement special handling for the qualified form,
        # which would only forbid storing specified headers.
        if not self._cache_private and response_cache_control.private:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as not cachable since the response contains the private directive."
                )
            )
            return False

        expires_presents = header_presents(response.headers, b"expires")
        # the response contains at least one of the following:
        # - a public response directive (see Section 5.2.2.9);
        # - a private response directive, if the cache is not shared (see Section 5.2.2.7);
        # - an Expires header field (see Section 5.3);
        # - a max-age response directive (see Section 5.2.2.1);
        # - if the cache is shared: an s-maxage response directive (see Section 5.2.2.10);
        # - a cache extension that allows it to be cached (see Section 5.2.3); or
        # - a status code that is defined as heuristically cacheable (see Section 4.2.2).
        if self._allow_heuristics and response.status in HEURISTICALLY_CACHEABLE_STATUS_CODES:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as cachable since its status code is heuristically cacheable."
                )
            )
            return True

        if not any(
            [
                response_cache_control.public,
                response_cache_control.private,
                expires_presents,
                response_cache_control.max_age is not None,
            ]
        ):
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as not cachable since it does not contain any of the required cache directives."
                )
            )
            return False

        logger.debug(
            (
                f"Considering the resource located at {get_safe_url(request.url)} "
                "as cachable since it meets the criteria for being stored in the cache."
            )
        )
        # response is a cachable!
        return True

    def _make_request_conditional(self, request: Request, response: Response) -> None:
        """
        Adds the precondition headers needed for response validation.

        This method will use the "Last-Modified" or "Etag" headers
        if they are provided in order to create precondition headers.

        See also (https://www.rfc-editor.org/rfc/rfc9111.html#name-sending-a-validation-reques)
        """

        if header_presents(response.headers, b"last-modified"):
            last_modified = extract_header_values(response.headers, b"last-modified", single=True)[0]
            logger.debug(
                (
                    f"Adding the 'If-Modified-Since' header with the value of '{last_modified.decode('ascii')}' "
                    f"to the request for the resource located at {get_safe_url(request.url)}."
                )
            )
        else:
            last_modified = None

        if header_presents(response.headers, b"etag"):
            etag = extract_header_values(response.headers, b"etag", single=True)[0]
            logger.debug(
                (
                    f"Adding the 'If-None-Match' header with the value of '{etag.decode('ascii')}' "
                    f"to the request for the resource located at {get_safe_url(request.url)}."
                )
            )
        else:
            etag = None

        precondition_headers: tp.List[tp.Tuple[bytes, bytes]] = []
        if last_modified:
            precondition_headers.append((b"If-Modified-Since", last_modified))
        if etag:
            precondition_headers.append((b"If-None-Match", etag))

        request.headers.extend(precondition_headers)

    def _validate_vary(self, request: Request, response: Response, original_request: Request) -> bool:
        """
        Determines whether the "vary" headers in the request and response headers are identical.

        See also (https://www.rfc-editor.org/rfc/rfc9111.html#name-calculating-cache-keys-with).
        """

        vary_headers = extract_header_values_decoded(response.headers, b"vary")
        vary = Vary.from_value(vary_values=vary_headers)
        for vary_header in vary._values:
            if vary_header == "*":
                return False  # pragma: no cover

            if extract_header_values(request.headers, vary_header) != extract_header_values(
                original_request.headers, vary_header
            ):
                return False

        return True

    def construct_response_from_cache(
        self, request: Request, response: Response, original_request: Request
    ) -> tp.Union[Response, Request, None]:
        """
        Specifies whether the response should be used, skipped, or validated by the cache.

        This method makes a decision regarding what to do with
        the stored response when it is retrieved from storage.
        It might be ready for use or it might need to be revalidated.
        This method mirrors the relevant section from RFC 9111,
        see (https://www.rfc-editor.org/rfc/rfc9111.html#name-constructing-responses-from).

        Returns:
            Response: This response is applicable to the request.
            Request: This response can be used for this request, but it must first be revalidated.
            None: It is not possible to use this response for this request.
        """

        # Use of responses with status codes 301 and 308 is always
        # legal as long as they don't adhere to any caching rules.
        if response.status in (301, 308):
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as valid for cache use since its status code is a permanent redirect."
                )
            )
            return response

        response_cache_control = parse_cache_control(extract_header_values_decoded(response.headers, b"Cache-Control"))
        request_cache_control = parse_cache_control(extract_header_values_decoded(request.headers, b"Cache-Control"))

        # request header fields nominated by the stored
        # response (if any) match those presented (see Section 4.1)
        if not self._validate_vary(request=request, response=response, original_request=original_request):
            # If the vary headers does not match, then do not use the response
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as invalid for cache use since the vary headers do not match."
                )
            )
            return None  # pragma: no cover

        # !!! this should be after the "vary" header validation.
        force_cache = request.extensions.get("force_cache", None)
        if force_cache if force_cache is not None else self._force_cache:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as valid for cache use since the request is forced to use the cache."
                )
            )
            return response

        # the stored response does not contain the
        # no-cache directive (Section 5.2.2.4), unless
        # it is successfully validated (Section 4.3)
        if (
            self._always_revalidate
            or response_cache_control.no_cache
            or response_cache_control.must_revalidate
            or request_cache_control.no_cache
        ):
            if self._always_revalidate:
                log_text = (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as needing revalidation since the cache is set to always revalidate."
                )
            elif response_cache_control.no_cache:
                log_text = (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as needing revalidation since the response contains the no-cache directive."
                )
            elif response_cache_control.must_revalidate:
                log_text = (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as needing revalidation since the response contains the must-revalidate directive."
                )
            elif request_cache_control.no_cache:
                log_text = (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as needing revalidation since the request contains the no-cache directive."
                )
            else:
                assert False, "Unreachable code "  # pragma: no cover
            logger.debug(log_text)
            self._make_request_conditional(request=request, response=response)
            return request

        freshness_lifetime = get_freshness_lifetime(response)

        if freshness_lifetime is None:
            logger.debug(
                (
                    "Could not determine the freshness lifetime of "
                    f"the resource located at {get_safe_url(request.url)}, "
                    "trying to use heuristics to calculate it."
                )
            )
            if self._allow_heuristics and response.status in HEURISTICALLY_CACHEABLE_STATUS_CODES:
                freshness_lifetime = get_heuristic_freshness(response=response, clock=self._clock)
                logger.debug(
                    (
                        f"Successfully calculated the freshness lifetime of the resource located at "
                        f"{get_safe_url(request.url)} using heuristics."
                    )
                )
            else:
                logger.debug(
                    (
                        "Could not calculate the freshness lifetime of "
                        f"the resource located at {get_safe_url(request.url)}. "
                        "Making a conditional request to revalidate the response."
                    )
                )
                # If Freshness cannot be calculated, then send the request
                self._make_request_conditional(request=request, response=response)
                return request

        age = get_age(response, self._clock)
        is_fresh = freshness_lifetime > age

        # The min-fresh request directive indicates that the client
        # prefers a response whose freshness lifetime is no less than
        #  its current age plus the specified time in seconds.
        # That is, the client wants a response that will still
        # be fresh for at least the specified number of seconds.
        if request_cache_control.min_fresh is not None:
            if freshness_lifetime < (age + request_cache_control.min_fresh):
                logger.debug(
                    (
                        f"Considering the resource located at {get_safe_url(request.url)} "
                        "as invalid for cache use since the time left for "
                        "freshness is less than the min-fresh directive."
                    )
                )
                return None

        # The max-stale request directive indicates that the
        # client will accept a response that has exceeded its freshness lifetime.
        # If a value is present, then the client is willing to accept a response
        # that has exceeded its freshness lifetime by no more than the specified
        # number of seconds. If no value is assigned to max-stale, then
        # the client will accept a stale response of any age.
        if not is_fresh and request_cache_control.max_stale is not None:
            exceeded_freshness_lifetime = age - freshness_lifetime

            if request_cache_control.max_stale < exceeded_freshness_lifetime:
                logger.debug(
                    (
                        f"Considering the resource located at {get_safe_url(request.url)} "
                        "as invalid for cache use since the freshness lifetime has been exceeded more than max-stale."
                    )
                )
                return None
            else:
                logger.debug(
                    (
                        f"Considering the resource located at {get_safe_url(request.url)} "
                        "as valid for cache use since the freshness lifetime has been exceeded less than max-stale."
                    )
                )
                return response

        # The max-age request directive indicates that
        # the client prefers a response whose age is
        # less than or equal to the specified number of seconds.
        # Unless the max-stale request directive is also present,
        # the client does not wish to receive a stale response.
        if request_cache_control.max_age is not None:
            if request_cache_control.max_age < age:
                logger.debug(
                    (
                        f"Considering the resource located at {get_safe_url(request.url)} "
                        "as invalid for cache use since the age of the response exceeds the max-age directive."
                    )
                )
                return None

        # the stored response is one of the following:
        #   fresh (see Section 4.2), or
        #   allowed to be served stale (see Section 4.2.4), or
        #   successfully validated (see Section 4.3).
        if is_fresh:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as valid for cache use since it is fresh."
                )
            )
            return response
        else:
            logger.debug(
                (
                    f"Considering the resource located at {get_safe_url(request.url)} "
                    "as needing revalidation since it is not fresh."
                )
            )
            # Otherwise, make a conditional request
            self._make_request_conditional(request=request, response=response)
            return request

    def handle_validation_response(self, old_response: Response, new_response: Response) -> Response:
        """
        Handles incoming validation response.

        This method takes care of what to do with the incoming
        validation response; if it is a 304 response, it updates
        the headers with the new response and returns it.

        This method mirrors the relevant section from RFC 9111,
        see (https://www.rfc-editor.org/rfc/rfc9111.html#name-handling-a-validation-respo).
        """
        if new_response.status == 304:
            headers = get_updated_headers(
                stored_response_headers=old_response.headers,
                new_response_headers=new_response.headers,
            )
            old_response.headers = headers
            return old_response
        else:
            return new_response
