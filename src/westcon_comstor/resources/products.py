"""Product resources: Availability and Pricing."""

from __future__ import annotations

import asyncio
import logging
from typing import List, Sequence

from .. import _endpoints as ep
from ..models.products import AvailabilityProduct, PricingResult
from .._endpoints import ProductLike
from ._base import AsyncResource, SyncResource

#: Products per request for :meth:`pricing_many`. The Pricing API returns AT MOST 10 products
#: per request and silently drops the rest (verified live 2026-09-28: 12 sent -> 10 returned,
#: no error), so a larger chunk loses products. Do not raise this above 10.
PRICING_CHUNK_SIZE = 10
#: Products per request for :meth:`availability_many`. Availability's cap is unverified (12/12
#: came back live), so it stays at the known-safe pricing cap until a higher one is verified.
AVAILABILITY_CHUNK_SIZE = 10
#: Backwards-compatible alias (was 40 before 26.9.28, which exceeded the Pricing API cap).
DEFAULT_CHUNK_SIZE = PRICING_CHUNK_SIZE
#: Chunks fetched at once by the async bulk helpers (bounded concurrency).
DEFAULT_CONCURRENCY = 4

logger = logging.getLogger("westcon_comstor")


def _log_isolating(group: Sequence[ProductLike]) -> None:
    # A "poison" SKU makes the Pricing API return a blank body for its whole request (verified
    # live 2026-09-28), so an empty multi-product chunk is re-asked one product at a time.
    logger.warning("pricing chunk of %d products returned no rows; retrying each product alone",
                   len(group))


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
        chunk_size: int = PRICING_CHUNK_SIZE,
    ) -> List[PricingResult]:
        """Pricing for many products in chunked requests (<= ``chunk_size`` products each).

        A long product list costs ``ceil(len / chunk_size)`` requests instead of one per
        product. Results are flattened in chunk order.

        The Pricing API returns at most 10 products per request and silently drops the rest,
        so ``chunk_size`` defaults to 10; a larger value loses products without any error.

        A chunk of several products that returns no rows (e.g. a "poison" SKU blanking the whole
        response) is retried one product per request, so one bad SKU cannot sink its neighbours.
        That costs at most ``chunk_size`` extra requests per such chunk; errors still propagate.
        """
        def _pricing(group: List[ProductLike]) -> List[PricingResult]:
            return self.pricing(
                country_code=country_code, currency=currency, products=group,
                customer_price=customer_price, partner_key=partner_key,
            )

        out: List[PricingResult] = []
        for group in _chunk(products, chunk_size):
            rows = _pricing(group)
            if not rows and len(group) > 1:
                _log_isolating(group)
                for product in group:
                    rows.extend(_pricing([product]))
            out.extend(rows)
        return out

    def availability_many(
        self,
        *,
        country_code: str,
        products: Sequence[ProductLike],
        partner_key: str | None = None,
        chunk_size: int = AVAILABILITY_CHUNK_SIZE,
    ) -> List[AvailabilityProduct]:
        """Availability for many products in chunked requests (<= ``chunk_size`` products each).

        ``chunk_size`` defaults to 10; the Availability API's per-request cap is unverified.
        """
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
        chunk_size: int = PRICING_CHUNK_SIZE,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> List[PricingResult]:
        """Pricing for many products: chunked (<= ``chunk_size`` per request) and fetched with
        bounded concurrency (``concurrency`` chunks at once). Results are flattened in chunk order.

        The Pricing API returns at most 10 products per request and silently drops the rest,
        so ``chunk_size`` defaults to 10; a larger value loses products without any error.

        A chunk of several products that returns no rows (e.g. a "poison" SKU blanking the whole
        response) is retried one product per request, sequentially within that chunk's
        concurrency slot, so one bad SKU cannot sink its neighbours. That costs at most
        ``chunk_size`` extra requests per such chunk; errors still propagate.
        """
        groups = _chunk(products, chunk_size)
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _pricing(group: List[ProductLike]) -> List[PricingResult]:
            return await self.pricing(
                country_code=country_code, currency=currency, products=group,
                customer_price=customer_price, partner_key=partner_key,
            )

        async def _one(group: List[ProductLike]) -> List[PricingResult]:
            async with sem:
                rows = await _pricing(group)
                if not rows and len(group) > 1:
                    _log_isolating(group)
                    for product in group:
                        rows.extend(await _pricing([product]))
                return rows

        results = await asyncio.gather(*[_one(g) for g in groups])
        return [r for group_res in results for r in group_res]

    async def availability_many(
        self,
        *,
        country_code: str,
        products: Sequence[ProductLike],
        partner_key: str | None = None,
        chunk_size: int = AVAILABILITY_CHUNK_SIZE,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> List[AvailabilityProduct]:
        """Availability for many products: chunked and fetched with bounded concurrency.

        ``chunk_size`` defaults to 10; the Availability API's per-request cap is unverified.
        """
        groups = _chunk(products, chunk_size)
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _one(group: List[ProductLike]) -> List[AvailabilityProduct]:
            async with sem:
                return await self.availability(
                    country_code=country_code, products=group, partner_key=partner_key,
                )

        results = await asyncio.gather(*[_one(g) for g in groups])
        return [r for group_res in results for r in group_res]
