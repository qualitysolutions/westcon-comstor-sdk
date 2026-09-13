"""Base classes for resource namespaces."""

from __future__ import annotations

from ..config import Config
from ..errors import ConfigurationError
from .._transport import AsyncTransport, SyncTransport


class _ResourceBase:
    def _partner_key(self, override: str | None) -> str:
        key = override or self._config.partner_key
        if not key:
            raise ConfigurationError(
                "partner_key is required: pass partner_key= to the call or set it on Config"
            )
        return key

    _config: Config


class SyncResource(_ResourceBase):
    def __init__(self, transport: SyncTransport, config: Config) -> None:
        self._t = transport
        self._config = config


class AsyncResource(_ResourceBase):
    def __init__(self, transport: AsyncTransport, config: Config) -> None:
        self._t = transport
        self._config = config
