"""Exception hierarchy for the Westcon-Comstor SDK.

All errors raised by the SDK derive from :class:`WestconComstorError`, so callers
can catch that single base type. Network/HTTP failures raise :class:`APIStatusError`
subclasses; malformed or business-level error payloads raise :class:`APIError`.
"""

from __future__ import annotations

from typing import Any


class WestconComstorError(Exception):
    """Base class for every error raised by this SDK."""


class ConfigurationError(WestconComstorError):
    """Raised when the client is misconfigured (missing credentials, etc.)."""


class AuthenticationError(WestconComstorError):
    """Raised when an OAuth2 token could not be obtained from Azure AD."""

    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class APIError(WestconComstorError):
    """Base class for errors returned by a Westcon-Comstor API call."""


class APIConnectionError(APIError):
    """Raised when the request could not be sent or no response was received."""


class APITimeoutError(APIConnectionError):
    """Raised when a request exceeds the configured timeout."""


class APIStatusError(APIError):
    """Raised when the API returns a non-2xx HTTP status.

    Attributes
    ----------
    status_code:
        The HTTP status code returned by the gateway.
    body:
        The parsed JSON body when available, otherwise the raw text.
    request_id:
        The APIM request id (``Ocp-Apim-Trace`` / ``request-id`` header) if present,
        useful when raising a support ticket with Westcon.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Any = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.request_id = request_id

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = super().__str__()
        if self.request_id:
            return f"{base} (status={self.status_code}, request_id={self.request_id})"
        return f"{base} (status={self.status_code})"


class BadRequestError(APIStatusError):
    """HTTP 400."""


class UnauthorizedError(APIStatusError):
    """HTTP 401 - token missing/expired/invalid."""


class ForbiddenError(APIStatusError):
    """HTTP 403 - authenticated but not permitted (e.g. subscription key)."""


class NotFoundError(APIStatusError):
    """HTTP 404."""


class UnprocessableEntityError(APIStatusError):
    """HTTP 422 - validation failed."""


class RateLimitError(APIStatusError):
    """HTTP 429."""


class ServerError(APIStatusError):
    """HTTP 5xx."""


_STATUS_TO_EXC: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def status_error_from_response(
    status_code: int,
    *,
    body: Any = None,
    request_id: str | None = None,
) -> APIStatusError:
    """Build the most specific :class:`APIStatusError` for ``status_code``."""
    exc_type = _STATUS_TO_EXC.get(status_code)
    if exc_type is None:
        exc_type = ServerError if status_code >= 500 else APIStatusError
    message = _message_from_body(body) or f"Westcon-Comstor API returned HTTP {status_code}"
    return exc_type(message, status_code=status_code, body=body, request_id=request_id)


def _message_from_body(body: Any) -> str | None:
    """Best-effort extraction of a human message from a Westcon error body.

    Westcon error shapes vary across APIs, e.g. ``{"success": false, "message": "..."}``,
    ``{"info": "..."}``, ``{"error": {"errorDescription": "..."}}`` and
    ``{"validationErrors": [...]}``.
    """
    if not isinstance(body, dict):
        return None
    for key in ("message", "info", "errorDescription", "error_description"):
        value = body.get(key)
        if isinstance(value, str) and value:
            return value
    error = body.get("error")
    if isinstance(error, dict):
        for key in ("errorDescription", "message"):
            value = error.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(error, str) and error:
        return error
    validation = body.get("validationErrors")
    if isinstance(validation, list) and validation:
        return "; ".join(str(v) for v in validation)
    return None
