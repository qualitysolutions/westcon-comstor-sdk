from __future__ import annotations

import httpx
import pytest

from westcon_comstor import Config, WestconComstorClient
from westcon_comstor.errors import AuthenticationError, ConfigurationError


def test_config_requires_credentials():
    with pytest.raises(ConfigurationError):
        Config(client_id="", client_secret="s", resource="r")


def test_token_is_fetched_once_and_cached(config, respx_mock):
    token_route = respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(
            200, json={"access_token": "T", "expires_on": "9999999999", "token_type": "Bearer"}
        )
    )
    invoice_route = respx_mock.post(f"{config.gateway_base_url}/OpenInvoiceList/GetList").mock(
        return_value=httpx.Response(200, json={"mT_InvoiceList_S_Resp": {"invoice": []}})
    )
    with WestconComstorClient(config) as client:
        client.invoices.list(start_date="20250101")
        client.invoices.list(start_date="20250201")

    assert token_route.call_count == 1  # cached across calls
    assert invoice_route.call_count == 2
    # Bearer + subscription key are attached.
    sent = invoice_route.calls[0].request
    assert sent.headers["Authorization"] == "Bearer T"
    assert sent.headers["Ocp-Apim-Subscription-Key"] == "sub-key"


def test_token_body_is_client_credentials(config, respx_mock):
    route = respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": "3600"})
    )
    respx_mock.post(f"{config.gateway_base_url}/OpenInvoiceList/GetList").mock(
        return_value=httpx.Response(200, json={"mT_InvoiceList_S_Resp": {"invoice": []}})
    )
    with WestconComstorClient(config) as client:
        client.invoices.list(start_date="20250101")
    body = route.calls[0].request.content.decode()
    assert "grant_type=client_credentials" in body
    assert "client_id=cid" in body
    assert "resource=res-guid" in body


def test_auth_failure_raises(config, respx_mock):
    respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(400, json={"error": "invalid_client"})
    )
    with WestconComstorClient(config) as client:
        with pytest.raises(AuthenticationError):
            client.invoices.list(start_date="20250101")


def test_401_triggers_single_token_refresh(config, respx_mock):
    respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_on": "9999999999"})
    )
    route = respx_mock.post(f"{config.gateway_base_url}/OpenInvoiceList/GetList")
    route.side_effect = [
        httpx.Response(401, json={"message": "expired"}),
        httpx.Response(200, json={"mT_InvoiceList_S_Resp": {"invoice": []}}),
    ]
    with WestconComstorClient(config) as client:
        result = client.invoices.list(start_date="20250101")
    assert result.invoice == []
    assert route.call_count == 2


def test_missing_partner_key_raises():
    cfg = Config(client_id="c", client_secret="s", resource="r")  # no partner_key
    with WestconComstorClient(cfg) as client:
        with pytest.raises(ConfigurationError):
            client.invoices.list(start_date="20250101")
