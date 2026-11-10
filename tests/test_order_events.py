from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import httpx
import pytest

from westcon_comstor import Config, WestconComstorClient
from westcon_comstor.models import OrderStatusEventBatch

from conftest import mock_token

POLL = "osm/api/OrderStatusMessages"
CONFIRM = "osmc/api/OrderStatusMessagesConfirm"

#: Anonymised excerpt of the live UAT response (2026-11-10): ORDER_CHANGED events, zero-padded
#: line numbers, empty customerLineNumber and every line delivered twice ~45 min apart.
UAT = json.loads((Path(__file__).parent / "fixtures" / "order_events_uat.json").read_text("utf-8"))


def _control(event_type: str, description: str = "", status_description: str = "Success") -> dict:
    return {"getOrderStatusMessageResponse": {"getOrderStatusMessageResult": {
        "totalEvents": 1, "batchID": 0, "events": [{
            "eRPOrderNumber": "", "customerOrderNumber": "", "eRPOrderLineNumber": "",
            "customerLineNumber": "", "lineStatusCode": "", "lineStatusDescription": "",
            "eventType": event_type, "eventDescription": description,
            "eventDate": "2026-11-10T04:03:00", "status": "200",
            "statusDescription": status_description,
        }]}}}


def _url(config: Config, path: str) -> str:
    return f"{config.gateway_base_url}/{path}"


def _body(route) -> dict:
    return json.loads(route.calls[-1].request.content.decode())


def test_poll_parses_live_uat_batch(client, config, respx_mock):
    route = respx_mock.post(_url(config, POLL)).mock(return_value=httpx.Response(200, json=UAT))

    batch = client.order_events.poll(timeout_seconds=10)

    assert _body(route) == {"getEventListenerMessage": {"eventListnerRequest": {
        "partnerKey": "PARTNER123", "timeoutInSeconds": 10, "startDate": "", "endDate": "",
    }}}
    assert batch.batch_id == 8
    assert batch.total_events == len(batch.events) == 7
    first = batch.events[0]
    assert first.event_type == "ORDER_CHANGED"
    assert first.erp_order_number == "0004000001"
    assert first.erp_order_line_number == "000010"
    assert first.customer_order_number == "Kund PO Åäö – 1"
    assert first.customer_line_number == ""
    assert (first.line_status_code, first.line_status_description) == ("INV", "Invoiced")
    assert first.event_datetime == datetime(2026, 10, 29, 8, 46, 43)
    # ORDER_CHANGED (live) counts as an order event even though the spec only names ORDER_UPDATED.
    assert len(batch.order_events) == 7
    assert batch.errors == []


def test_latest_per_line_dedupes_repeated_deliveries():
    batch = OrderStatusEventBatch.model_validate(
        UAT["getOrderStatusMessageResponse"]["getOrderStatusMessageResult"]
    )
    latest = batch.latest_per_line()
    assert [(e.line_key, e.line_status_code, e.event_date) for e in latest] == [
        (("0004000001", "000010"), "INV", "2026-10-29T09:31:30"),
        (("0004000002", "000150"), "POC", "2026-10-29T09:31:30"),
        (("0004000002", "000210"), "REJ", "2026-10-29T09:31:30"),
        (("0004000003", "000010"), "POC", "2026-10-29T09:31:29"),
    ]


def test_spec_sample_order_updated_and_short_line_numbers():
    # The documented sample: ORDER_UPDATED, unpadded line number "10".
    batch = OrderStatusEventBatch.model_validate({"totalEvents": 1, "batchID": 33, "events": [{
        "eRPOrderNumber": "0000000003", "customerOrderNumber": "Sample1",
        "eRPOrderLineNumber": "10", "customerLineNumber": "1", "lineStatusCode": "SHI",
        "lineStatusDescription": "Shipped", "eventType": "ORDER_UPDATED",
        "eventDescription": "Order has been updated", "eventDate": "2023-08-14T15:51:25",
        "status": "200", "statusDescription": "Success"}]})
    (event,) = batch.order_events
    assert event.line_key == ("0000000003", "000010")


@pytest.mark.parametrize("raw", [
    _control("RECONNECT", "Connection has timed out, reconnect to wait for additional messages"),
    _control("NODATA", "No data found", "No messages found for selected date range"),
    _control(""),  # live idle response: empty eventType (not in the spec)
])
def test_control_responses_have_no_order_events(client, config, respx_mock, raw):
    respx_mock.post(_url(config, POLL)).mock(return_value=httpx.Response(200, json=raw))
    batch = client.order_events.poll()
    assert batch.batch_id == 0
    assert len(batch.events) == 1 and batch.events[0].is_control
    assert batch.order_events == [] and batch.errors == []


def test_error_event_is_surfaced():
    batch = OrderStatusEventBatch.model_validate({"batchID": 0, "events": [{
        "eRPOrderNumber": "", "eventType": "ERROR", "status": "500",
        "statusDescription": "Invalid partner key"}]})
    assert [e.status_description for e in batch.errors] == ["Invalid partner key"]
    assert batch.order_events == []


@pytest.mark.parametrize("raw", [None, "", {}, {"getOrderStatusMessageResponse": None}])
def test_empty_or_missing_body_is_an_empty_batch(client, config, respx_mock, raw):
    respx_mock.post(_url(config, POLL)).mock(
        return_value=httpx.Response(200, json=raw) if raw is not None else httpx.Response(200)
    )
    batch = client.order_events.poll()
    assert (batch.batch_id, batch.total_events, batch.events) == (0, 0, [])


def test_single_event_object_is_listified():
    batch = OrderStatusEventBatch.model_validate(
        {"batchID": 5, "events": {"eRPOrderNumber": "9", "eventType": "ORDER_UPDATED"}}
    )
    assert [e.erp_order_number for e in batch.order_events] == ["9"]


def test_poll_date_range_accepts_dates_and_strings(client, config, respx_mock):
    route = respx_mock.post(_url(config, POLL)).mock(return_value=httpx.Response(200, json=UAT))
    client.order_events.poll(start_date=date(2026, 10, 29), end_date="20261030")
    inner = _body(route)["getEventListenerMessage"]["eventListnerRequest"]
    assert (inner["startDate"], inner["endDate"]) == ("20261029", "20261030")


@pytest.mark.parametrize("timeout", [4, 301])
def test_poll_rejects_out_of_range_timeout(client, timeout):
    with pytest.raises(ValueError):
        client.order_events.poll(timeout_seconds=timeout)


def test_poll_read_timeout_exceeds_long_poll(client, config, respx_mock):
    route = respx_mock.post(_url(config, POLL)).mock(return_value=httpx.Response(200, json=UAT))
    client.order_events.poll(timeout_seconds=300)
    assert route.calls[-1].request.extensions["timeout"]["read"] == 330.0


def test_other_endpoints_keep_the_client_timeout(client, config, respx_mock):
    route = respx_mock.post(_url(config, CONFIRM)).mock(return_value=httpx.Response(200, json={}))
    client.order_events.confirm(8)
    assert route.calls[-1].request.extensions["timeout"]["read"] == config.timeout


def test_order_event_subscription_key_overrides_default(config, respx_mock):
    osm = Config(client_id="cid", client_secret="secret", resource="res-guid",
                 subscription_key="sub-key", order_event_subscription_key="osm-key",
                 partner_key="PARTNER123", max_retries=0)
    mock_token(respx_mock, osm)
    poll = respx_mock.post(_url(osm, POLL)).mock(return_value=httpx.Response(200, json=UAT))
    confirm = respx_mock.post(_url(osm, CONFIRM)).mock(return_value=httpx.Response(200, json={}))
    other = respx_mock.post(_url(osm, "Orders/orderStatus")).mock(
        return_value=httpx.Response(200, json={"MT_OrderStatus_Response": []})
    )
    with WestconComstorClient(osm) as c:
        c.order_events.poll()
        c.order_events.confirm(8)
        c.orders.status(["1"])
    assert poll.calls[-1].request.headers["Ocp-Apim-Subscription-Key"] == "osm-key"
    assert confirm.calls[-1].request.headers["Ocp-Apim-Subscription-Key"] == "osm-key"
    assert other.calls[-1].request.headers["Ocp-Apim-Subscription-Key"] == "sub-key"


def test_without_order_event_key_the_default_key_is_used(client, config, respx_mock):
    route = respx_mock.post(_url(config, POLL)).mock(return_value=httpx.Response(200, json=UAT))
    client.order_events.poll()
    assert route.calls[-1].request.headers["Ocp-Apim-Subscription-Key"] == "sub-key"


def test_confirm_complete_and_partial(client, config, respx_mock):
    route = respx_mock.post(_url(config, CONFIRM)).mock(
        return_value=httpx.Response(200, json={"status": "200", "statusDescription": "Success"})
    )
    assert client.order_events.confirm(33).ok
    assert _body(route) == {"partnerKey": "PARTNER123", "batchID": 33}
    client.order_events.confirm(33, order_numbers=["Sample2"])
    assert _body(route) == {"partnerKey": "PARTNER123", "batchID": 33, "orderNumbers": ["Sample2"]}


@pytest.mark.parametrize("raw, ok", [
    ({"status": "200", "statusDescription": "Success"}, True),
    ({"status": "500", "statusDescription": "Batch not found"}, False),
    (None, True),  # empty 2xx body: nothing contradicts the HTTP success
])
def test_confirm_result_ok(client, config, respx_mock, raw, ok):
    respx_mock.post(_url(config, CONFIRM)).mock(
        return_value=httpx.Response(200, json=raw) if raw is not None else httpx.Response(200)
    )
    assert client.order_events.confirm(8).ok is ok


def test_from_env_reads_order_event_subscription_key(monkeypatch):
    for k in ("WESTCON_CLIENT_ID", "WESTCON_CLIENT_SECRET", "WESTCON_RESOURCE"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("WESTCON_ENV", "uat")
    monkeypatch.setenv("WESTCON_ORDER_EVENT_SUBSCRIPTION_KEY", "generic")
    monkeypatch.setenv("WESTCON_UAT_ORDER_EVENT_SUBSCRIPTION_KEY", "uat-osm")
    assert Config.from_env().order_event_subscription_key == "uat-osm"
    monkeypatch.delenv("WESTCON_UAT_ORDER_EVENT_SUBSCRIPTION_KEY")
    assert Config.from_env().order_event_subscription_key == "generic"


async def test_async_poll_and_confirm(async_client, config, respx_mock):
    respx_mock.post(_url(config, POLL)).mock(return_value=httpx.Response(200, json=UAT))
    route = respx_mock.post(_url(config, CONFIRM)).mock(
        return_value=httpx.Response(200, json={"status": "200", "statusDescription": "Success"})
    )
    batch = await async_client.order_events.poll(timeout_seconds=5)
    assert len(batch.latest_per_line()) == 4
    assert (await async_client.order_events.confirm(batch.batch_id)).ok
    assert _body(route) == {"partnerKey": "PARTNER123", "batchID": 8}
