from __future__ import annotations

import httpx
import pytest

from westcon_comstor.errors import (
    BadRequestError,
    NotFoundError,
    ServerError,
    UnprocessableEntityError,
)


def _url(config, path):
    return f"{config.gateway_base_url}/{path}"


@pytest.mark.parametrize(
    "status,exc",
    [
        (400, BadRequestError),
        (404, NotFoundError),
        (422, UnprocessableEntityError),
        (500, ServerError),
    ],
)
def test_status_errors(client, config, respx_mock, status, exc):
    respx_mock.post(_url(config, "OpenInvoiceList/GetList")).mock(
        return_value=httpx.Response(
            status, json={"message": "boom"}, headers={"request-id": "abc-123"}
        )
    )
    with pytest.raises(exc) as info:
        client.invoices.list(start_date="20250101")
    assert info.value.status_code == status
    assert info.value.request_id == "abc-123"
    assert "boom" in str(info.value)


def test_error_message_from_validation_errors(client, config, respx_mock):
    respx_mock.post(_url(config, "OpenInvoiceList/GetList")).mock(
        return_value=httpx.Response(
            422, json={"validationErrors": ["Email already in use"], "status": 422}
        )
    )
    with pytest.raises(UnprocessableEntityError) as info:
        client.invoices.list(start_date="20250101")
    assert "Email already in use" in str(info.value)


async def test_async_availability(async_client, config, respx_mock):
    respx_mock.post(_url(config, "api/products/availability")).mock(
        return_value=httpx.Response(
            200,
            json={"Availability_Response": [{"ProductNumber": "C1111-4P"}]},
        )
    )
    products = await async_client.products.availability(
        country_code="AU", products=[{"product_number": "C1111-4P"}]
    )
    assert products[0].product_number == "C1111-4P"
