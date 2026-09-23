"""Python SDK for the Westcon-Comstor AIM (API Integration Management) APIs.

Quick start::

    from westcon_comstor import WestconComstorClient

    with WestconComstorClient(
        client_id="...", client_secret="...", resource="...",
        subscription_key="...", partner_key="...",
    ) as client:
        invoices = client.invoices.list(start_date="20250101", end_date="20250201")
        for inv in invoices.invoice:
            print(inv.billing_document, inv.total_value, inv.currency)

All credentials are issued by Westcon-Comstor. See ``README.md`` for the full API map.
"""

from __future__ import annotations

import logging

from .client import AsyncWestconComstorClient, WestconComstorClient
from .config import Config
from .errors import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConfigurationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    UnprocessableEntityError,
    WestconComstorError,
)

__version__ = "26.9.23"

# Library logging is silent unless the host app configures a handler. The SDK logs to the
# "westcon_comstor" logger at DEBUG (request path, timing, request_id) and WARNING (retries)
# and never logs credentials, tokens, headers, or request/response bodies.
logging.getLogger("westcon_comstor").addHandler(logging.NullHandler())

__all__ = [
    "__version__",
    "WestconComstorClient",
    "AsyncWestconComstorClient",
    "Config",
    # errors
    "WestconComstorError",
    "ConfigurationError",
    "AuthenticationError",
    "APIError",
    "APIConnectionError",
    "APITimeoutError",
    "APIStatusError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "UnprocessableEntityError",
    "RateLimitError",
    "ServerError",
]
