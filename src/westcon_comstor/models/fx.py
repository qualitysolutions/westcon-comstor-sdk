"""Models for the derived-FX tool (implied exchange rates from the Pricing API)."""

from __future__ import annotations

import statistics
from typing import List, Optional

from .common import WestconModel


class ProductRate(WestconModel):
    """The implied rate derived from one product's list price in two currencies."""

    product_number: str
    base_price: float
    quote_price: float
    rate: float  # quote_price / base_price


class ImpliedRate(WestconModel):
    """Comstor's effective exchange rate for ``base_currency`` -> ``quote_currency``.

    Derived by pricing the same product(s) in both currencies and dividing the returned
    list prices. ``rate`` is the aggregate (median by default); the per-product
    ``samples`` let you see the spread and spot SKUs priced natively in one currency.
    """

    base_currency: str
    quote_currency: str
    country: str
    price_field: str  # "list" or "customer"
    rate: Optional[float] = None  # aggregate (median of samples)
    mean: Optional[float] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    spread: Optional[float] = None  # (max - min) / median
    sample_count: int = 0
    samples: List[ProductRate] = []
    skipped: List[str] = []  # requested products missing a price in one currency


def compute_implied_rate(
    *,
    base_currency: str,
    quote_currency: str,
    country: str,
    price_field: str,
    base_prices: dict[str, float],
    quote_prices: dict[str, float],
    requested: List[str],
) -> ImpliedRate:
    """Combine two ``{productNumber: listPrice}`` maps into an :class:`ImpliedRate`."""
    samples: List[ProductRate] = []
    for number in requested:
        base_price = base_prices.get(number)
        quote_price = quote_prices.get(number)
        if not base_price or not quote_price:
            continue
        samples.append(
            ProductRate(
                product_number=number,
                base_price=base_price,
                quote_price=quote_price,
                rate=quote_price / base_price,
            )
        )
    rates = [s.rate for s in samples]
    skipped = [n for n in requested if n not in base_prices or n not in quote_prices]

    result = ImpliedRate(
        base_currency=base_currency,
        quote_currency=quote_currency,
        country=country,
        price_field=price_field,
        sample_count=len(samples),
        samples=samples,
        skipped=skipped,
    )
    if rates:
        median = statistics.median(rates)
        result.rate = median
        result.mean = statistics.fmean(rates)
        result.minimum = min(rates)
        result.maximum = max(rates)
        result.spread = (max(rates) - min(rates)) / median if median else None
    return result
