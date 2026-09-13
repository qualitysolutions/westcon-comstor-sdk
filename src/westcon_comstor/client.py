"""Public sync and async clients for the Westcon-Comstor AIM APIs."""

from __future__ import annotations

from typing import Any, Mapping

import httpx

from ._transport import AsyncTransport, SyncTransport
from .config import Config
from .resources import (
    AccountsResource,
    AemResource,
    AsyncAccountsResource,
    AsyncAemResource,
    AsyncFxResource,
    AsyncInvoicesResource,
    AsyncOrdersResource,
    AsyncProductsResource,
    AsyncQuotesResource,
    AsyncShippingResource,
    FxResource,
    InvoicesResource,
    OrdersResource,
    ProductsResource,
    QuotesResource,
    ShippingResource,
)


def _coerce_config(config: Config | None, kwargs: dict[str, Any]) -> Config:
    if config is not None:
        if kwargs:
            raise TypeError("Pass either a Config or credential keyword arguments, not both")
        return config
    return Config.from_env(**kwargs)


class WestconComstorClient:
    """Synchronous client for the Westcon-Comstor AIM APIs.

    Construct with an explicit :class:`Config`, with credential keyword arguments, or
    with nothing (reads ``WESTCON_*`` environment variables)::

        client = WestconComstorClient(
            client_id="...", client_secret="...", resource="...",
            subscription_key="...", partner_key="...",
        )
        invoices = client.invoices.list(start_date="20250101", end_date="20250201")

    Use it as a context manager to close the underlying HTTP connection pool.
    """

    def __init__(
        self,
        config: Config | None = None,
        *,
        http_client: httpx.Client | None = None,
        **credentials: Any,
    ) -> None:
        self._config = _coerce_config(config, credentials)
        self._transport = SyncTransport(self._config, client=http_client)

        self.invoices = InvoicesResource(self._transport, self._config)
        self.orders = OrdersResource(self._transport, self._config)
        self.products = ProductsResource(self._transport, self._config)
        self.quotes = QuotesResource(self._transport, self._config)
        self.shipping = ShippingResource(self._transport, self._config)
        self.accounts = AccountsResource(self._transport, self._config)
        self.aem = AemResource(self._transport, self._config)
        self.fx = FxResource(self._transport, self._config)

    @property
    def config(self) -> Config:
        return self._config

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
        """Escape hatch: make an arbitrary authenticated gateway call.

        ``path`` may be relative to the gateway base URL or an absolute URL. Returns the
        parsed JSON body. Useful for endpoints not yet wrapped with typed methods
        (e.g. PartnerView).
        """
        return self._transport.request(
            method, path, json=json, params=params, headers=headers, authenticated=authenticated
        )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "WestconComstorClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncWestconComstorClient:
    """Asynchronous client for the Westcon-Comstor AIM APIs.

    Mirrors :class:`WestconComstorClient` but every resource method is a coroutine::

        async with AsyncWestconComstorClient() as client:
            result = await client.products.availability(
                country_code="AU", products=[{"product_number": "C1111-4P"}]
            )
    """

    def __init__(
        self,
        config: Config | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        **credentials: Any,
    ) -> None:
        self._config = _coerce_config(config, credentials)
        self._transport = AsyncTransport(self._config, client=http_client)

        self.invoices = AsyncInvoicesResource(self._transport, self._config)
        self.orders = AsyncOrdersResource(self._transport, self._config)
        self.products = AsyncProductsResource(self._transport, self._config)
        self.quotes = AsyncQuotesResource(self._transport, self._config)
        self.shipping = AsyncShippingResource(self._transport, self._config)
        self.accounts = AsyncAccountsResource(self._transport, self._config)
        self.aem = AsyncAemResource(self._transport, self._config)
        self.fx = AsyncFxResource(self._transport, self._config)

    @property
    def config(self) -> Config:
        return self._config

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
        return await self._transport.request(
            method, path, json=json, params=params, headers=headers, authenticated=authenticated
        )

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncWestconComstorClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
