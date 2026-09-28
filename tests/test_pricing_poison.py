"""Poison-SKU handling: the live Pricing API returns HTTP 200 with a whitespace-only, non-JSON
body for some SKUs (verified 2026-09-28 with MV2-HW), and that body replaces the answer for
EVERY product in the same request."""

from __future__ import annotations

import json

import httpx
import pytest

from westcon_comstor.errors import APIError, APIStatusError

POISON_BODY = "\r\n  \r\n"
POISON_SKU = "MV2-HW"


def _url(config, path: str) -> str:
    return f"{config.gateway_base_url}/{path}"


def _poisoned_pricing_api(request: httpx.Request) -> httpx.Response:
    """Like the live API: caps at 10 products, and a poison SKU among them blanks the body."""
    sent = json.loads(request.content.decode())["mT_Pricing_S_Req"]["pricing"]["products"][:10]
    if any(p["productNumber"] == POISON_SKU for p in sent):
        return httpx.Response(200, text=POISON_BODY)
    return httpx.Response(200, json={"MT_Pricing_Resp": [
        {"product": {"productNumber": p["productNumber"], "listPrice": 1.0}} for p in sent
    ]})


def _twelve_with_poison() -> list[dict[str, str]]:
    skus = [f"P{i}" for i in range(12)]
    skus[3] = POISON_SKU
    return [{"product_number": s} for s in skus]


def _expected_without_poison() -> list[str]:
    return [p["product_number"] for p in _twelve_with_poison() if p["product_number"] != POISON_SKU]


# --- parse: whitespace body -> no rows; other non-JSON -> APIError -----------
def test_whitespace_pricing_body_is_no_rows(client, config, respx_mock):
    respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text=POISON_BODY)
    )
    assert client.products.pricing(
        country_code="SE", currency="SEK", products=[{"product_number": POISON_SKU}]
    ) == []


def test_whitespace_availability_body_is_no_rows(client, config, respx_mock):
    respx_mock.post(_url(config, "api/products/availability")).mock(
        return_value=httpx.Response(200, text=POISON_BODY)
    )
    assert client.products.availability(
        country_code="SE", products=[{"product_number": POISON_SKU}]
    ) == []


@pytest.mark.parametrize("path, call", [
    ("Pricing/RetrievePrice", lambda c: c.products.pricing(
        country_code="SE", currency="SEK", products=[{"product_number": "X"}])),
    ("api/products/availability", lambda c: c.products.availability(
        country_code="SE", products=[{"product_number": "X"}])),
])
def test_other_non_json_body_raises_api_error(client, config, respx_mock, path, call):
    respx_mock.post(_url(config, path)).mock(
        return_value=httpx.Response(200, text="<html>Service Unavailable</html>")
    )
    with pytest.raises(APIError, match="non-JSON body"):
        call(client)


async def test_async_whitespace_pricing_body_is_no_rows(async_client, config, respx_mock):
    respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text=POISON_BODY)
    )
    assert await async_client.products.pricing(
        country_code="SE", currency="SEK", products=[{"product_number": POISON_SKU}]
    ) == []


# --- pricing_many: a poison SKU cannot sink its neighbours -------------------
def test_pricing_many_isolates_poison_sku(client, config, respx_mock):
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        side_effect=_poisoned_pricing_api
    )
    results = client.products.pricing_many(
        country_code="SE", currency="SEK", products=_twelve_with_poison()
    )
    assert [r.product.product_number for r in results] == _expected_without_poison()
    # chunk 1 (10 products, blanked) + 10 single-product retries + chunk 2 (2 products)
    assert route.call_count == 1 + 10 + 1


async def test_async_pricing_many_isolates_poison_sku(async_client, config, respx_mock):
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        side_effect=_poisoned_pricing_api
    )
    results = await async_client.products.pricing_many(
        country_code="SE", currency="SEK", products=_twelve_with_poison()
    )
    assert [r.product.product_number for r in results] == _expected_without_poison()
    assert route.call_count == 1 + 10 + 1


def test_pricing_many_single_product_empty_chunk_is_not_retried(client, config, respx_mock):
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text=POISON_BODY)
    )
    assert client.products.pricing_many(
        country_code="SE", currency="SEK", products=[{"product_number": POISON_SKU}]
    ) == []
    assert route.call_count == 1


def test_pricing_many_does_not_fan_out_on_status_error(client, config, respx_mock):
    # An outage must not be multiplied by per-product retries: errors propagate as before.
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    with pytest.raises(APIStatusError):
        client.products.pricing_many(
            country_code="SE", currency="SEK", products=_twelve_with_poison()
        )
    assert route.call_count == 1
