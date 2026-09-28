"""A03 "Vendor Obsolete" products: the live Pricing API sends otherwise valid JSON with an EMPTY
value (``"listPrice" : ,``) for them, which made the whole body unparseable. Bodies below are the
REAL live responses (verified 2026-09-28), layout and whitespace kept; prices replaced."""

from __future__ import annotations

import json

import httpx
import pytest

from westcon_comstor.errors import APIError

OBSOLETE_BODY = (
    '\n'
    '                                                    {\n'
    '  "MT_Pricing_Resp" : \n'
    '  [\n'
    '      {\n'
    '\n'
    '        "product" : \n'
    '        {\n'
    '          "productNumber" : "MV2-HW",\n'
    '          "longProductNumber" : "MV2-HW",\n'
    '          "listPrice" : ,\n'
    '          "currency" : ""\n'
    '        }\n'
    '       ,\n'
    '         "error" : \n'
    '        {\n'
    '          "errorNumber" : "A03",\n'
    '          "errorDescription" : "Vendor Obsolete"\n'
    '        }\n'
    '\n'
    '     }\n'
    '  ]\n'
    '\n'
    '}'
)

BATCH_BODY = (
    '\n'
    '                                                    {\n'
    '  "MT_Pricing_Resp" : \n'
    '  [\n'
    '      {\n'
    '\n'
    '        "product" : \n'
    '        {\n'
    '          "productNumber" : "MV2-HW",\n'
    '          "longProductNumber" : "MV2-HW",\n'
    '          "listPrice" : ,\n'
    '          "currency" : ""\n'
    '        }\n'
    '       ,\n'
    '         "error" : \n'
    '        {\n'
    '          "errorNumber" : "A03",\n'
    '          "errorDescription" : "Vendor Obsolete"\n'
    '        }\n'
    '\n'
    '     },\n'
    '      {\n'
    '\n'
    '        "product" : \n'
    '        {\n'
    '          "productNumber" : "MR36-HW",\n'
    '          "longProductNumber" : "MR36-HW",\n'
    '          "listPrice" : 1.0 ,\n'
    '          "customerPrice" : 2.0 ,\n'
    '          "currency" : "SEK"\n'
    '        }\n'
    '\n'
    '     },\n'
    '      {\n'
    '\n'
    '        "product" : \n'
    '        {\n'
    '          "productNumber" : "MX85-HW",\n'
    '          "longProductNumber" : "MX85-HW",\n'
    '          "listPrice" : 3.0 ,\n'
    '          "customerPrice" : 4.0 ,\n'
    '          "currency" : "SEK"\n'
    '        }\n'
    '\n'
    '     }\n'
    '  ]\n'
    '\n'
    '}\n'
    '\n'
    '                                        '
)

BATCH_SKUS = ["MR36-HW", "MV2-HW", "MX85-HW"]


def _url(config, path: str) -> str:
    return f"{config.gateway_base_url}/{path}"


def _assert_obsolete_row(row) -> None:
    assert row.product.product_number == "MV2-HW"
    assert row.product.list_price is None
    assert row.error.error_number == "A03"
    assert row.error.error_description == "Vendor Obsolete"


def test_raw_bodies_are_invalid_json():
    # Guards the fixtures: they must reproduce the live defect, not a cleaned-up version.
    for body in (OBSOLETE_BODY, BATCH_BODY):
        with pytest.raises(json.JSONDecodeError):
            json.loads(body)


def test_pricing_returns_obsolete_row_with_its_error(client, config, respx_mock):
    respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text=OBSOLETE_BODY)
    )
    rows = client.products.pricing(
        country_code="SE", currency="SEK", products=[{"product_number": "MV2-HW"}]
    )
    assert len(rows) == 1
    _assert_obsolete_row(rows[0])


def test_pricing_many_keeps_every_row_when_one_is_obsolete(client, config, respx_mock):
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text=BATCH_BODY)
    )
    rows = client.products.pricing_many(
        country_code="SE", currency="SEK", products=[{"product_number": s} for s in BATCH_SKUS]
    )
    assert route.call_count == 1  # parsed as-is: no per-product retry
    by_sku = {r.product.product_number: r for r in rows}
    assert sorted(by_sku) == sorted(BATCH_SKUS)
    _assert_obsolete_row(by_sku["MV2-HW"])
    assert by_sku["MR36-HW"].product.list_price == 1.0 and by_sku["MR36-HW"].error is None
    assert by_sku["MX85-HW"].product.customer_price == 4.0


async def test_async_pricing_many_keeps_every_row_when_one_is_obsolete(
    async_client, config, respx_mock
):
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text=BATCH_BODY)
    )
    rows = await async_client.products.pricing_many(
        country_code="SE", currency="SEK", products=[{"product_number": s} for s in BATCH_SKUS]
    )
    assert route.call_count == 1
    assert sorted(r.product.product_number for r in rows) == sorted(BATCH_SKUS)


def test_unrepairable_text_body_still_raises_api_error(client, config, respx_mock):
    respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(200, text="<html>Service Unavailable</html>")
    )
    with pytest.raises(APIError, match="non-JSON body"):
        client.products.pricing(
            country_code="SE", currency="SEK", products=[{"product_number": "X"}]
        )
