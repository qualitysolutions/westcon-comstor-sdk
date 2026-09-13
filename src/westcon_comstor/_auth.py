"""OAuth 2.0 client-credentials token handling (Azure AD v1).

All Westcon-Comstor transactional APIs are protected by an Azure AD v1
client-credentials flow: POST ``client_id``/``client_secret``/``grant_type``/``resource``
as ``application/x-www-form-urlencoded`` to the tenant token endpoint and use the
returned ``access_token`` as a Bearer token.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Config
from .errors import AuthenticationError

logger = logging.getLogger("westcon_comstor")


@dataclass(frozen=True)
class AccessToken:
    """A cached bearer token and the monotonic-ish time it becomes stale."""

    value: str
    #: Wall-clock epoch seconds after which the token should be refreshed.
    expires_at: float

    def is_valid(self, *, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) < self.expires_at


class OAuth2ClientCredentials:
    """Fetches and parses Azure AD client-credentials tokens.

    The instance itself is stateless (no caching); callers own the cache so that the
    sync and async clients can each manage concurrency in their own idiom.
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def _form_body(self) -> dict[str, str]:
        return {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "grant_type": "client_credentials",
            "resource": self._config.resource,
        }

    def fetch_sync(self, client: httpx.Client) -> AccessToken:
        try:
            response = client.post(
                self._config.token_url,
                data=self._form_body(),
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:  # network-level failure
            raise AuthenticationError(f"Failed to reach the Azure AD token endpoint: {exc}") from exc
        return self._parse(response)

    async def fetch_async(self, client: httpx.AsyncClient) -> AccessToken:
        try:
            response = await client.post(
                self._config.token_url,
                data=self._form_body(),
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise AuthenticationError(f"Failed to reach the Azure AD token endpoint: {exc}") from exc
        return self._parse(response)

    def _parse(self, response: httpx.Response) -> AccessToken:
        if response.status_code != 200:
            body = _safe_json(response)
            raise AuthenticationError(
                "Azure AD rejected the client-credentials request",
                status_code=response.status_code,
                body=body,
            )
        data: dict[str, Any] = response.json()
        token = data.get("access_token")
        if not token:
            raise AuthenticationError("Token response did not contain an access_token", body=data)
        expires_at = self._compute_expiry(data)
        # Never log the token value; only its lifetime.
        logger.debug("obtained access token (valid ~%ds)", int(expires_at - time.time()))
        return AccessToken(value=token, expires_at=expires_at - self._config.token_expiry_leeway)

    @staticmethod
    def _compute_expiry(data: dict[str, Any]) -> float:
        """Derive an absolute expiry epoch from the token response.

        Azure AD v1 returns both ``expires_on`` (absolute epoch, as a string) and
        ``expires_in`` (relative seconds, as a string). Prefer the absolute value.
        """
        expires_on = data.get("expires_on")
        if expires_on is not None:
            try:
                return float(expires_on)
            except (TypeError, ValueError):
                pass
        expires_in = data.get("expires_in")
        try:
            return time.time() + float(expires_in)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            # Conservative fallback: assume a short-lived token.
            return time.time() + 300.0


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
