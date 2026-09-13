"""Derived-FX resource: Comstor's implied exchange rates via the Pricing API.

There is no exchange-rate endpoint. Comstor's pricing engine converts a product's base
price into whatever ``currency`` you request, so pricing the *same* product in two
currencies and dividing the returned list prices yields the effective rate Comstor uses.

Give one product for a quick read, or several to verify the rate is consistent (the tool
returns per-product samples plus the median). Uses ``listPrice`` by default so
account-specific discounts don't skew the ratio.
"""

from __future__ import annotations

from typing import Any, List, Sequence

from .. import _endpoints as ep
from ..models.fx import ImpliedRate, compute_implied_rate
from ._base import AsyncResource, SyncResource

Products = Any  # str | ProductRef | Mapping | Sequence[those]


class FxResource(SyncResource):
    def implied_rate(
        self,
        *,
        base: str,
        quote: str,
        products: Products,
        country: str = "SE",
        price_field: str = "list",
        partner_key: str | None = None,
    ) -> ImpliedRate:
        """Comstor's implied ``base`` -> ``quote`` rate from one or more products.

        e.g. ``implied_rate(base="USD", quote="SEK", products="SW-FWSWS-ASG-S500")``.
        ``price_field`` is ``"list"`` (default) or ``"customer"``.
        """
        key = self._partner_key(partner_key)
        payload, requested = ep.normalize_products(products)
        base_prices = self._prices(key, country, base, payload, price_field)
        quote_prices = self._prices(key, country, quote, payload, price_field)
        return compute_implied_rate(
            base_currency=base,
            quote_currency=quote,
            country=country,
            price_field=price_field,
            base_prices=base_prices,
            quote_prices=quote_prices,
            requested=requested,
        )

    def rates(
        self,
        *,
        bases: Sequence[str],
        quote: str,
        products: Products,
        country: str = "SE",
        price_field: str = "list",
        partner_key: str | None = None,
    ) -> List[ImpliedRate]:
        """Implied rates for several base currencies against one ``quote`` currency.

        The ``quote`` prices are fetched once and reused across all pairs, so
        ``rates(bases=["EUR", "USD"], quote="SEK", products=[...])`` costs 3 pricing calls.
        """
        key = self._partner_key(partner_key)
        payload, requested = ep.normalize_products(products)
        quote_prices = self._prices(key, country, quote, payload, price_field)
        out: List[ImpliedRate] = []
        for base in bases:
            base_prices = self._prices(key, country, base, payload, price_field)
            out.append(
                compute_implied_rate(
                    base_currency=base,
                    quote_currency=quote,
                    country=country,
                    price_field=price_field,
                    base_prices=base_prices,
                    quote_prices=quote_prices,
                    requested=requested,
                )
            )
        return out

    def _prices(
        self, key: str, country: str, currency: str, payload: Sequence[Any], price_field: str
    ) -> dict[str, float]:
        customer_flag = "Y" if price_field == "customer" else "N"
        body = ep.build_pricing(key, country, customer_flag, currency, payload)
        raw = self._t.request("POST", ep.PATH_PRICING, json=body)
        return ep.prices_by_product(ep.parse_pricing(raw), price_field=price_field)


class AsyncFxResource(AsyncResource):
    async def implied_rate(
        self,
        *,
        base: str,
        quote: str,
        products: Products,
        country: str = "SE",
        price_field: str = "list",
        partner_key: str | None = None,
    ) -> ImpliedRate:
        key = self._partner_key(partner_key)
        payload, requested = ep.normalize_products(products)
        base_prices = await self._prices(key, country, base, payload, price_field)
        quote_prices = await self._prices(key, country, quote, payload, price_field)
        return compute_implied_rate(
            base_currency=base,
            quote_currency=quote,
            country=country,
            price_field=price_field,
            base_prices=base_prices,
            quote_prices=quote_prices,
            requested=requested,
        )

    async def rates(
        self,
        *,
        bases: Sequence[str],
        quote: str,
        products: Products,
        country: str = "SE",
        price_field: str = "list",
        partner_key: str | None = None,
    ) -> List[ImpliedRate]:
        key = self._partner_key(partner_key)
        payload, requested = ep.normalize_products(products)
        quote_prices = await self._prices(key, country, quote, payload, price_field)
        out: List[ImpliedRate] = []
        for base in bases:
            base_prices = await self._prices(key, country, base, payload, price_field)
            out.append(
                compute_implied_rate(
                    base_currency=base,
                    quote_currency=quote,
                    country=country,
                    price_field=price_field,
                    base_prices=base_prices,
                    quote_prices=quote_prices,
                    requested=requested,
                )
            )
        return out

    async def _prices(
        self, key: str, country: str, currency: str, payload: Sequence[Any], price_field: str
    ) -> dict[str, float]:
        customer_flag = "Y" if price_field == "customer" else "N"
        body = ep.build_pricing(key, country, customer_flag, currency, payload)
        raw = await self._t.request("POST", ep.PATH_PRICING, json=body)
        return ep.prices_by_product(ep.parse_pricing(raw), price_field=price_field)
