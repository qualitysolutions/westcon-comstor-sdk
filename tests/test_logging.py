from __future__ import annotations

import logging

import httpx

from westcon_comstor import WestconComstorClient


def test_logs_request_and_never_leaks_secrets(config, respx_mock, caplog):
    respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "SUPERSECRETTOKEN",
                                               "expires_on": "9999999999"})
    )
    respx_mock.post(f"{config.gateway_base_url}/OpenInvoiceList/GetList").mock(
        return_value=httpx.Response(200, json={"mT_InvoiceList_S_Resp": {"invoice": []}},
                                    headers={"request-id": "req-abc"})
    )
    with caplog.at_level(logging.DEBUG, logger="westcon_comstor"):
        with WestconComstorClient(config) as client:
            client.invoices.list(start_date="20250101")

    text = "\n".join(r.getMessage() for r in caplog.records)
    # Useful diagnostics are present...
    assert "OpenInvoiceList/GetList" in text
    assert "request_id=req-abc" in text
    assert "obtained access token" in text
    # ...but no secrets ever appear in the logs.
    for secret in ("SUPERSECRETTOKEN", config.client_secret, config.subscription_key,
                   config.partner_key):
        assert secret not in text


def test_retry_is_logged_at_warning(config, respx_mock, caplog):
    config.max_retries = 1
    respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_on": "9999999999"})
    )
    route = respx_mock.post(f"{config.gateway_base_url}/OpenInvoiceList/GetList")
    route.side_effect = [
        httpx.Response(503, json={"message": "busy"}),
        httpx.Response(200, json={"mT_InvoiceList_S_Resp": {"invoice": []}}),
    ]
    with caplog.at_level(logging.WARNING, logger="westcon_comstor"):
        with WestconComstorClient(config) as client:
            client.invoices.list(start_date="20250101")
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("returned 503" in m and "retrying" in m for m in warnings)
