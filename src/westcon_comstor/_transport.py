"""Low-level HTTP transport shared by the sync and async clients.

Responsibilities:
  * acquire and cache the OAuth2 bearer token (refreshing when stale),
  * attach the ``Authorization`` and ``Ocp-Apim-Subscription-Key`` headers,
  * retry idempotently on transient network errors, 429 and 5xx,
  * map non-2xx responses to the SDK exception hierarchy.

The two transports intentionally duplicate their small send loops because httpx's
sync and async APIs are not interchangeable; the request-building and
response-handling helpers are shared as free functions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Mapping

import httpx

from ._auth import AccessToken, OAuth2ClientCredentials
from .config import Config
from .errors import (
    APIConnectionError,
    APITimeoutError,
    UnauthorizedError,
    status_error_from_response,
)

logger = logging.getLogger("westcon_comstor")

_SUBSCRIPTION_KEY_HEADER = "Ocp-Apim-Subscription-Key"
_REQUEST_ID_HEADERS = (
    "request-id",
    "apim-request-id",
    "x-ms-request-id",
    "ocp-apim-trace-location",
)
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def _request_id(headers: httpx.Headers) -> str | None:
    for name in _REQUEST_ID_HEADERS:
        value: str | None = headers.get(name)
        if value:
            return value
    return None


def _parse_body(response: httpx.Response) -> Any:
    """Parse a response body as JSON when possible, else return text.

    Some Westcon endpoints (e.g. Availability) return JSON with a non-JSON
    ``Content-Type``, and a few double-encode JSON as a string, so we parse based on the
    content rather than trusting the header.
    """
    if not response.content:
        return None
    text = response.text
    data = _try_json(text)
    if data is None:
        return text
    # Handle bodies that are a JSON string wrapping more JSON.
    if isinstance(data, str):
        nested = _try_json(data)
        if nested is not None and not isinstance(nested, str):
            return nested
    return data


def _try_json(text: str) -> Any:
    stripped = text.lstrip()
    if not stripped or stripped[0] not in "{[\"":
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _handle_response(response: httpx.Response) -> Any:
    """Return the parsed body for a 2xx response, else raise an APIStatusError."""
    if 200 <= response.status_code < 300:
        return _parse_body(response)
    raise status_error_from_response(
        response.status_code,
        body=_parse_body(response),
        request_id=_request_id(response.headers),
    )


def _log_response(method: str, url: str, response: httpx.Response, started: float) -> None:
    """Log the outcome of a request at DEBUG (no bodies/headers -> no secrets/PII)."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    elapsed_ms = (time.perf_counter() - started) * 1000
    rid = _request_id(response.headers)
    logger.debug(
        "%s %s -> %d (%.0f ms)%s",
        method, url, response.status_code, elapsed_ms, f" request_id={rid}" if rid else "",
    )


def _backoff_seconds(attempt: int, response: httpx.Response | None) -> float:
    """Exponential backoff, honouring ``Retry-After`` on 429/503 when present."""
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
    return min(2.0**attempt * 0.5, 8.0)


class SyncTransport:
    """Synchronous transport backed by :class:`httpx.Client`."""

    def __init__(self, config: Config, *, client: httpx.Client | None = None) -> None:
        self._config = config
        self._auth = OAuth2ClientCredentials(config)
        self._token: AccessToken | None = None
        self._lock = threading.Lock()
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=config.timeout,
            verify=config.verify_tls,
        )

    # -- token management ------------------------------------------------
    def _get_token(self, *, force_refresh: bool = False) -> str:
        with self._lock:
            if force_refresh or self._token is None or not self._token.is_valid():
                self._token = self._auth.fetch_sync(self._client)
            return self._token.value

    # -- request ---------------------------------------------------------
    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        authenticated: bool = True,
    ) -> Any:
        url = _build_url(self._config, path)
        attempt = 0
        token_retried = False
        while True:
            request_headers = _build_headers(
                self._config,
                token=self._get_token() if authenticated else None,
                extra=headers,
            )
            logger.debug("%s %s (attempt %d)", method, url, attempt + 1)
            started = time.perf_counter()
            try:
                response = self._client.request(
                    method, url, json=json, params=params, headers=request_headers
                )
            except httpx.TimeoutException as exc:
                if attempt < self._config.max_retries:
                    logger.warning("timeout on %s %s; retrying (%d/%d)", method, url,
                                   attempt + 1, self._config.max_retries)
                    time.sleep(_backoff_seconds(attempt, None))
                    attempt += 1
                    continue
                raise APITimeoutError(f"Request to {url} timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                if attempt < self._config.max_retries:
                    logger.warning("network error on %s %s: %s; retrying (%d/%d)", method, url,
                                   exc, attempt + 1, self._config.max_retries)
                    time.sleep(_backoff_seconds(attempt, None))
                    attempt += 1
                    continue
                raise APIConnectionError(f"Request to {url} failed: {exc}") from exc

            _log_response(method, url, response, started)
            if response.status_code == 401 and authenticated and not token_retried:
                # Token may have been revoked/expired server-side; refresh once.
                logger.debug("401 on %s %s; refreshing token and retrying once", method, url)
                token_retried = True
                self._get_token(force_refresh=True)
                continue
            if response.status_code in _RETRY_STATUSES and attempt < self._config.max_retries:
                logger.warning("%s %s returned %d; retrying (%d/%d)", method, url,
                               response.status_code, attempt + 1, self._config.max_retries)
                time.sleep(_backoff_seconds(attempt, response))
                attempt += 1
                continue
            return _handle_response(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "SyncTransport":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncTransport:
    """Asynchronous transport backed by :class:`httpx.AsyncClient`."""

    def __init__(self, config: Config, *, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._auth = OAuth2ClientCredentials(config)
        self._token: AccessToken | None = None
        self._lock = asyncio.Lock()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.verify_tls,
        )

    async def _get_token(self, *, force_refresh: bool = False) -> str:
        async with self._lock:
            if force_refresh or self._token is None or not self._token.is_valid():
                self._token = await self._auth.fetch_async(self._client)
            return self._token.value

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        authenticated: bool = True,
    ) -> Any:
        url = _build_url(self._config, path)
        attempt = 0
        token_retried = False
        while True:
            request_headers = _build_headers(
                self._config,
                token=(await self._get_token()) if authenticated else None,
                extra=headers,
            )
            logger.debug("%s %s (attempt %d)", method, url, attempt + 1)
            started = time.perf_counter()
            try:
                response = await self._client.request(
                    method, url, json=json, params=params, headers=request_headers
                )
            except httpx.TimeoutException as exc:
                if attempt < self._config.max_retries:
                    logger.warning("timeout on %s %s; retrying (%d/%d)", method, url,
                                   attempt + 1, self._config.max_retries)
                    await asyncio.sleep(_backoff_seconds(attempt, None))
                    attempt += 1
                    continue
                raise APITimeoutError(f"Request to {url} timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                if attempt < self._config.max_retries:
                    logger.warning("network error on %s %s: %s; retrying (%d/%d)", method, url,
                                   exc, attempt + 1, self._config.max_retries)
                    await asyncio.sleep(_backoff_seconds(attempt, None))
                    attempt += 1
                    continue
                raise APIConnectionError(f"Request to {url} failed: {exc}") from exc

            _log_response(method, url, response, started)
            if response.status_code == 401 and authenticated and not token_retried:
                logger.debug("401 on %s %s; refreshing token and retrying once", method, url)
                token_retried = True
                await self._get_token(force_refresh=True)
                continue
            if response.status_code in _RETRY_STATUSES and attempt < self._config.max_retries:
                logger.warning("%s %s returned %d; retrying (%d/%d)", method, url,
                               response.status_code, attempt + 1, self._config.max_retries)
                await asyncio.sleep(_backoff_seconds(attempt, response))
                attempt += 1
                continue
            return _handle_response(response)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


# -- shared helpers ------------------------------------------------------
def _build_url(config: Config, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{config.gateway_base_url}/{path.lstrip('/')}"


def _build_headers(
    config: Config,
    *,
    token: str | None,
    extra: Mapping[str, str] | None,
) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    headers.update(config.default_headers)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if config.subscription_key:
        headers[_SUBSCRIPTION_KEY_HEADER] = config.subscription_key
    if extra:
        headers.update(extra)
    return headers
