"""Product resources: Availability and Pricing."""

from __future__ import annotations

from typing import List, Sequence

from .. import _endpoints as ep
from ..models.products import AvailabilityProduct, PricingResult
from .._endpoints import ProductLike
from ._base import AsyncResource, SyncResource


class ProductsResource(SyncResource):
    def availability(
        self,
        *,
        country_code: str,
        products: Sequence[ProductLike],
        partner_key: str | None = None,
    ) -> List[AvailabilityProduct]:
        """Return stock availability per product for a country.

        ``products`` is a sequence of :class:`ProductRef` or dicts with
        ``product_number`` / ``long_product_number``.
        """
        payload = ep.build_availability(self._partner_key(partner_key), country_code, products)
        raw = self._t.request("POST", ep.PATH_AVAILABILITY, json=payload)
        return ep.parse_availability(raw)

    def pricing(
        self,
        *,
        country_code: str,
        currency: str,
        products: Sequence[ProductLike],
        customer_price: str = "Y",
        partner_key: str | None = None,
    ) -> List[PricingResult]:
        """Return list and (optionally) customer pricing per product.

        ``customer_price`` is ``"Y"`` or ``"N"``.
        """
        payload = ep.build_pricing(
            self._partner_key(partner_key), country_code, customer_price, currency, products
        )
        raw = self._t.request("POST", ep.PATH_PRICING, json=payload)
        return ep.parse_pricing(raw)


class AsyncProductsResource(AsyncResource):
    async def availability(
        self,
        *,
        country_code: str,
        products: Sequence[ProductLike],
        partner_key: str | None = None,
    ) -> List[AvailabilityProduct]:
        payload = ep.build_availability(self._partner_key(partner_key), country_code, products)
        raw = await self._t.request("POST", ep.PATH_AVAILABILITY, json=payload)
        return ep.parse_availability(raw)

    async def pricing(
        self,
        *,
        country_code: str,
        currency: str,
        products: Sequence[ProductLike],
        customer_price: str = "Y",
        partner_key: str | None = None,
    ) -> List[PricingResult]:
        payload = ep.build_pricing(
            self._partner_key(partner_key), country_code, customer_price, currency, products
        )
        raw = await self._t.request("POST", ep.PATH_PRICING, json=payload)
        return ep.parse_pricing(raw)
