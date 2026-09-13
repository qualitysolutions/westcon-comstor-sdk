from __future__ import annotations

import json

import httpx

# List prices per currency for two products (P1, P2). Ratios are consistent per pair:
#   SEK/USD = 1085/100 = 10.85 ; SEK/EUR = 1085/95 = 11.4210...
PRICES = {
    "USD": {"P1": 100.0, "P2": 200.0},
    "EUR": {"P1": 95.0, "P2": 190.0},
    "SEK": {"P1": 1085.0, "P2": 2170.0},
}


def _pricing_side_effect(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    pricing = body["mT_Pricing_S_Req"]["pricing"]
    currency = pricing["currency"]
    table = PRICES[currency]
    resp = []
    for prod in pricing["products"]:
        number = prod["productNumber"]
        if number in table:
            resp.append({"product": {"productNumber": number, "listPrice": table[number]}})
    return httpx.Response(200, json={"MT_Pricing_Resp": resp})


def _mock_pricing(config, respx_mock):
    route = respx_mock.post(f"{config.gateway_base_url}/Pricing/RetrievePrice")
    route.side_effect = _pricing_side_effect
    return route


def test_fx_implied_rate_single_pair(client, config, respx_mock):
    _mock_pricing(config, respx_mock)
    result = client.fx.implied_rate(base="USD", quote="SEK", products=["P1", "P2"], country="SE")
    assert result.base_currency == "USD"
    assert result.quote_currency == "SEK"
    assert result.sample_count == 2
    assert result.rate == 10.85
    assert result.minimum == result.maximum == 10.85
    assert result.spread == 0.0
    assert {s.product_number for s in result.samples} == {"P1", "P2"}


def test_fx_rates_multiple_bases(client, config, respx_mock):
    _mock_pricing(config, respx_mock)
    results = client.fx.rates(
        bases=["EUR", "USD"], quote="SEK", products=["P1", "P2"], country="SE"
    )
    by_base = {r.base_currency: r for r in results}
    assert round(by_base["USD"].rate, 4) == 10.85
    assert round(by_base["EUR"].rate, 4) == 11.4211
    assert by_base["EUR"].quote_currency == "SEK"


def test_fx_single_product_and_skip(client, config, respx_mock):
    _mock_pricing(config, respx_mock)
    # "P3" is priced in neither table -> skipped; a bare string is accepted.
    result = client.fx.implied_rate(base="USD", quote="SEK", products="P1", country="SE")
    assert result.rate == 10.85
    assert result.sample_count == 1

    result2 = client.fx.implied_rate(base="USD", quote="SEK", products=["P1", "P3"], country="SE")
    assert result2.sample_count == 1
    assert "P3" in result2.skipped


def test_fx_list_price_uses_customer_flag_N(client, config, respx_mock):
    route = _mock_pricing(config, respx_mock)
    client.fx.implied_rate(base="USD", quote="SEK", products=["P1"], country="SE")
    # listPrice path must request customerPrice="N".
    for call in route.calls:
        body = json.loads(call.request.content.decode())
        assert body["mT_Pricing_S_Req"]["pricing"]["customerPrice"] == "N"
