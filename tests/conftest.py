from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from westcon_comstor import Config, WestconComstorClient
from westcon_comstor.client import AsyncWestconComstorClient

TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/token"


@pytest.fixture
def config() -> Config:
    return Config(
        client_id="cid",
        client_secret="secret",
        resource="res-guid",
        subscription_key="sub-key",
        partner_key="PARTNER123",
        max_retries=0,
    )


def mock_token(respx_mock, config: Config) -> None:
    respx_mock.post(config.token_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "token_type": "Bearer",
                "expires_in": "3600",
                "expires_on": "9999999999",
                "access_token": "TESTTOKEN",
            },
        )
    )


@pytest.fixture
def client(config: Config, respx_mock):
    mock_token(respx_mock, config)
    c = WestconComstorClient(config)
    yield c
    c.close()


@pytest.fixture
async def async_client(config: Config, respx_mock):
    mock_token(respx_mock, config)
    c = AsyncWestconComstorClient(config)
    yield c
    await c.aclose()


@pytest.fixture
def capped_pricing_api() -> Callable[[httpx.Request], httpx.Response]:
    """respx side effect mimicking the live Pricing API: it returns at most 10 products per
    request and silently drops the rest (verified 2026-09-28: 12 sent -> 10 returned)."""

    def _handler(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content.decode())["mT_Pricing_S_Req"]["pricing"]["products"]
        return httpx.Response(200, json={"MT_Pricing_Resp": [
            {"product": {"productNumber": p["productNumber"], "listPrice": 1.0}} for p in sent[:10]
        ]})

    return _handler
