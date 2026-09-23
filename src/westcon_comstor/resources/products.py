"""Product resources: Availability and Pricing."""

from __future__ import annotations

import asyncio
from typing import List, Sequence

from .. import _endpoints as ep
from ..models.products import AvailabilityProduct, PricingResult
from .._endpoints import ProductLike
from ._base import AsyncResource, SyncResource

#: Products per request for the ``*_many`` bulk helpers. The pricing/availability APIs accept
#: many products in one call; chunking keeps a single request from getting too large.
DEFAULT_CHUNK_SIZE = 40
#: Chunks fetched at once by the async bulk helpers (bounded concurrency).
DEFAULT_CONCURRENCY = 4


def _chunk(products: Sequence[ProductLike], size: int) -> List[List[ProductLike]]:
    size = max(1, size)
    items = list(products)
    return [items[i:i + size] for i in range(0, len(items), size)]


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

    def pricing_many(
        self,
        *,
        country_code: str,
        currency: str,
        products: Sequence[ProductLike],
        customer_price: str = "Y",
        partner_key: str | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> List[PricingResult]:
        """Pricing for many products in chunked requests (<= ``chunk_size`` products each).

        A long product list costs ``ceil(len / chunk_size)`` requests instead of one per
        product. Results are flattened in chunk order.
        """
        out: List[PricingResult] = []
        for group in _chunk(products, chunk_size):
            out.extend(self.pricing(
                country_code=country_code, currency=currency, products=group,
                customer_price=customer_price, partner_key=partner_key,
            ))
        return out

    def availability_many(
        self,
        *,
        country_code: str,
        products: Sequence[ProductLike],
        partner_key: str | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> List[AvailabilityProduct]:
        """Availability for many products in chunked requests (<= ``chunk_size`` products each)."""
        out: List[AvailabilityProduct] = []
        for group in _chunk(products, chunk_size):
            out.extend(self.availability(
                country_code=country_code, products=group, partner_key=partner_key,
            ))
        return out


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

    async def pricing_many(
        self,
        *,
        country_code: str,
        currency: str,
        products: Sequence[ProductLike],
        customer_price: str = "Y",
        partner_key: str | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> List[PricingResult]:
        """Pricing for many products: chunked (<= ``chunk_size`` per request) and fetched with
        bounded concurrency (``concurrency`` chunks at once). Results are flattened in chunk order.
        """
        groups = _chunk(products, chunk_size)
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _one(group: List[ProductLike]) -> List[PricingResult]:
            async with sem:
                return await self.pricing(
                    country_code=country_code, currency=currency, products=group,
                    customer_price=customer_price, partner_key=partner_key,
                )

        results = await asyncio.gather(*[_one(g) for g in groups])
        return [r for group_res in results for r in group_res]

    async def availability_many(
        self,
        *,
        country_code: str,
        products: Sequence[ProductLike],
        partner_key: str | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> List[AvailabilityProduct]:
        """Availability for many products: chunked and fetched with bounded concurrency."""
        groups = _chunk(products, chunk_size)
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _one(group: List[ProductLike]) -> List[AvailabilityProduct]:
            async with sem:
                return await self.availability(
                    country_code=country_code, products=group, partner_key=partner_key,
                )

        results = await asyncio.gather(*[_one(g) for g in groups])
        return [r for group_res in results for r in group_res]
