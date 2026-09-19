from __future__ import annotations

import json

import httpx

from westcon_comstor.config import Config


def _url(config: Config, path: str) -> str:
    return f"{config.gateway_base_url}/{path}"


def _body(route) -> dict:
    return json.loads(route.calls[-1].request.content.decode())


def test_open_invoice_list(client, config, respx_mock):
    route = respx_mock.post(_url(config, "OpenInvoiceList/GetList")).mock(
        return_value=httpx.Response(
            200,
            json={
                "mT_InvoiceList_S_Resp": {
                    "invoice": [
                        {
                            "billingDocument": "BD1",
                            "eRPOrderNumber": "ERP1",
                            "totalValue": "100",
                            "currency": "EUR",
                        }
                    ],
                    "error": {"error": "", "errorDescription": ""},
                }
            },
        )
    )
    result = client.invoices.list(start_date="20250101", end_date="20250201")
    assert _body(route) == {
        "mT_InvoiceList_S_Req": {
            "partnerKey": "PARTNER123",
            "startDate": "20250101",
            "endDate": "20250201",
        }
    }
    assert result.invoice[0].billing_document == "BD1"
    assert result.invoice[0].erp_order_number == "ERP1"  # eRPOrderNumber alias
    assert result.invoice[0].currency == "EUR"


def test_open_order_list(client, config, respx_mock):
    route = respx_mock.post(_url(config, "OpenOrders/GetList")).mock(
        return_value=httpx.Response(
            200,
            json={
                "mT_OpenOrderList_S_Resp": {
                    "openOrderList": [
                        {"salesOrderNumber": "SO1", "customerPONumber": "PO9", "amount": "10"}
                    ],
                    "error": {},
                }
            },
        )
    )
    result = client.orders.open_order_list(start_date="20250101")
    assert _body(route)["mT_OpenOrderList_Req"]["partnerKey"] == "PARTNER123"
    assert result.open_order_list[0].sales_order_number == "SO1"
    assert result.open_order_list[0].customer_po_number == "PO9"  # customerPONumber alias


def test_open_order_list_pascalcase_container(client, config, respx_mock):
    # Live API returns the container as "OpenOrderList" (PascalCase), not the documented
    # "openOrderList" - must still parse.
    respx_mock.post(_url(config, "OpenOrders/GetList")).mock(
        return_value=httpx.Response(
            200,
            json={"mT_OpenOrderList_S_Resp": {
                "OpenOrderList": [{"salesOrderNumber": "0000000002", "amount": "1000.00",
                                   "currency": "SEK", "endUserName": "Example Customer AB"}]}},
        )
    )
    result = client.orders.open_order_list(start_date="20230101")
    assert len(result.open_order_list) == 1
    assert result.open_order_list[0].sales_order_number == "0000000002"
    assert result.open_order_list[0].end_user_name == "Example Customer AB"


def test_order_status_with_string_orders(client, config, respx_mock):
    route = respx_mock.post(_url(config, "Orders/orderStatus")).mock(
        return_value=httpx.Response(
            200,
            json={
                "MT_OrderStatus_Response": [
                    {
                        "eRPOrderNumber": "000059",
                        "eRPProductNumber": "CISCO1",
                        "lineStatusCode": "INC",
                        "estimatedShipDate": "20250101",
                        "parentERPLine": "000000",
                    }
                ]
            },
        )
    )
    lines = client.orders.status(["600014", "600019"])
    sent = _body(route)["mT_OrderStatus_API_REQ"]
    assert sent["order"] == ["600014", "600019"]
    assert sent["orderType"] == "W"
    assert lines[0].erp_order_number == "000059"
    assert lines[0].erp_product_number == "CISCO1"
    assert lines[0].estimated_ship_date == "20250101"
    assert lines[0].parent_erp_line == "000000"


def test_invoiced_lines_helper(client, config, respx_mock):
    respx_mock.post(_url(config, "Orders/orderStatus")).mock(
        return_value=httpx.Response(
            200,
            json={"MT_OrderStatus_Response": [
                {"eRPOrderLineNumber": "000010", "lineStatusCode": "INV",
                 "billingDocument": "9000000003", "eRPProductNumber": "LIC-MG21"},
                {"eRPOrderLineNumber": "000110", "lineStatusCode": "REJ",
                 "eRPProductNumber": "MR44-HW"},
                {"eRPOrderLineNumber": "000120", "lineStatusCode": "INV",
                 "billingDocument": "9000000005", "eRPProductNumber": "LIC-ENT"},
            ]},
        )
    )
    lines = client.orders.invoiced_lines("0000000004")
    assert len(lines) == 2  # only INV lines
    assert {l.billing_document for l in lines} == {"9000000003", "9000000005"}
    assert all(l.line_status_code == "INV" for l in lines)


def test_invoices_grouped_by_invoice(client, config, respx_mock):
    respx_mock.post(_url(config, "Orders/orderStatus")).mock(
        return_value=httpx.Response(
            200,
            json={"MT_OrderStatus_Response": [
                {"eRPOrderLineNumber": "000010", "lineStatusCode": "INV", "billingDocument": "INV_A"},
                {"eRPOrderLineNumber": "000020", "lineStatusCode": "INV", "billingDocument": "INV_A"},
                {"eRPOrderLineNumber": "000030", "lineStatusCode": "REJ"},
                {"eRPOrderLineNumber": "000040", "lineStatusCode": "INV", "billingDocument": "INV_B"},
            ]},
        )
    )
    invoices = client.orders.invoices("0000000004")
    assert [inv.invoice_number for inv in invoices] == ["INV_A", "INV_B"]  # first-seen order
    assert [len(inv.lines) for inv in invoices] == [2, 1]
    assert invoices[0].lines[0].erp_order_line_number == "000010"


def test_availability_pascalcase_response(client, config, respx_mock):
    route = respx_mock.post(_url(config, "api/products/availability")).mock(
        return_value=httpx.Response(
            200,
            json={
                "Availability_Response": [
                    {
                        "ProductNumber": "C1111-4P",
                        "storage_locations": [
                            {"Plant": "P1", "AvailableQuantity": 5, "AvailableOnDate": "2026-09-19",
                             "LeadTimeInDays": 2}
                        ],
                        "error": {"errorNumber": "", "errorDescription": ""},
                    }
                ]
            },
        )
    )
    products = client.products.availability(
        country_code="AU", products=[{"product_number": "C1111-4P"}]
    )
    sent = _body(route)["Availability_Request"]
    assert sent["countryCode"] == "AU"
    assert sent["products"] == [{"productNumber": "C1111-4P"}]
    assert products[0].product_number == "C1111-4P"
    assert products[0].storage_locations[0].plant == "P1"
    assert products[0].storage_locations[0].available_quantity == 5.0
    assert products[0].storage_locations[0].available_on_date == "2026-09-19"


def test_availability_json_with_non_json_content_type(client, config, respx_mock):
    # Availability returns JSON but with a text/plain content-type; must still parse.
    body = '{"Availability_Response":[{"ProductNumber":"C1111-4P",'\
           '"storage_locations":[{"Plant":"P1","AvailableQuantity":5}]}]}'
    respx_mock.post(_url(config, "api/products/availability")).mock(
        return_value=httpx.Response(200, text=body, headers={"content-type": "text/plain"})
    )
    products = client.products.availability(
        country_code="AU", products=[{"product_number": "C1111-4P"}]
    )
    assert products[0].product_number == "C1111-4P"
    assert products[0].storage_locations[0].available_quantity == 5.0


def test_double_encoded_json_body(client, config, respx_mock):
    # Body is a JSON string that itself contains JSON.
    inner = '{"mT_InvoiceList_S_Resp":{"invoice":[{"billingDocument":"BD1"}]}}'
    respx_mock.post(_url(config, "OpenInvoiceList/GetList")).mock(
        return_value=httpx.Response(200, json=inner)  # json= a string -> double-encoded
    )
    result = client.invoices.list(start_date="20250101")
    assert result.invoice[0].billing_document == "BD1"


def test_pricing(client, config, respx_mock):
    route = respx_mock.post(_url(config, "Pricing/RetrievePrice")).mock(
        return_value=httpx.Response(
            200,
            json={
                "MT_Pricing_Resp": [
                    {
                        "product": {
                            "productNumber": "ASG",
                            "listPrice": 28.0,
                            "customerPrice": 2.8,
                            "currency": "EUR",
                        }
                    }
                ]
            },
        )
    )
    from westcon_comstor.models.products import ProductRef

    results = client.products.pricing(
        country_code="DE", currency="EUR", products=[ProductRef(product_number="ASG")]
    )
    sent = _body(route)["mT_Pricing_S_Req"]["pricing"]
    assert sent["customerPrice"] == "Y"
    assert sent["products"] == [{"productNumber": "ASG"}]
    assert results[0].product.list_price == 28.0
    assert results[0].product.customer_price == 2.8


def test_get_quote(client, config, respx_mock):
    route = respx_mock.post(_url(config, "QuoteDetail/retrieve")).mock(
        return_value=httpx.Response(
            200,
            json={
                "message": "ok",
                "success": True,
                "quoteData": {
                    "code": "0812",
                    "totalItems": 2,
                    "deliveryCost": {"currencyIso": "GBP", "value": 0, "formattedValue": "GBP 0.00"},
                    "entries": [
                        {
                            "customerLineNumber": "1",
                            "totalInclVAT": 2.8,
                            "vRFLines": [{"fieldName": "F", "value": "V"}],
                            "product": {"code": "M0", "includedInTheBox": True},
                        }
                    ],
                },
            },
        )
    )
    quote = client.quotes.get(quote_id="0812", reseller_id="R1", version="0")
    assert _body(route) == {
        "partnerKey": "PARTNER123",
        "resellerId": "R1",
        "quoteId": "0812",
        "version": "0",
    }
    assert quote.success is True
    assert quote.quote_data.code == "0812"
    assert quote.quote_data.delivery_cost.currency_iso == "GBP"
    entry = quote.quote_data.entries[0]
    assert entry.total_incl_vat == 2.8  # totalInclVAT alias
    assert entry.vrf_lines[0].field_name == "F"  # vRFLines alias
    assert entry.product.included_in_the_box is True


def test_carrier_tracking(client, config, respx_mock):
    route = respx_mock.post(_url(config, "CarrierTracking/GetTrackingInfo")).mock(
        return_value=httpx.Response(
            200,
            json={
                "shipmentTrackingResponse": {
                    "shipmentTrackingResult": {
                        "orderNumber": "201201",
                        "carrier": "DHL",
                        "serviceEvents": [{"eventLocation": "Brussels-BE"}],
                        "errorCode": "OK",
                    }
                }
            },
        )
    )
    result = client.shipping.carrier_tracking(
        order_number="201201", carrier="DHL", tracking_number="JD01"
    )
    sent = _body(route)["shipmentTracking"]["mT_ShipmentTracking_API_Req"]
    assert sent["trackingNumber"] == "JD01"
    assert result.order_number == "201201"
    assert result.service_events[0].event_location == "Brussels-BE"
    assert result.error_code == "OK"


def test_shipment_detail(client, config, respx_mock):
    route = respx_mock.post(_url(config, "shipping/ShipmentDetail")).mock(
        return_value=httpx.Response(
            200,
            json={
                "mT_OrderTrack_Response": {
                    "OrderStatus": [{"ERPOrderNumber": "0009", "LineStatusCode": "INV"}],
                    "OrderTracking": [{"TrackingNo": "155011", "Carrier": "Fed"}],
                    "OrderSerialNum": [{"ManufSerialNo": "S440", "MACAddress": "AA:BB"}],
                    "OrderVRFData": [{"Name": "n", "Value": "v"}],
                }
            },
        )
    )
    result = client.shipping.shipment_detail(order_number="59XXXX", tracking_data="Y")
    sent = _body(route)["mT_OrderTrack_API_Req"]
    assert sent["orderNumber"] == "59XXXX"
    assert sent["trackingData"] == "Y"
    assert result.order_status[0].erp_order_number == "0009"
    assert result.order_tracking[0].tracking_no == "155011"
    assert result.order_serial_num[0].mac_address == "AA:BB"
    assert result.order_vrf_data[0].name == "n"


def test_shipment_detail_without_envelope(client, config, respx_mock):
    # Live shipment_detail omits the mT_OrderTrack_Response envelope and returns the
    # inner object directly -- sometimes with a single key (serial_data only).
    respx_mock.post(_url(config, "shipping/ShipmentDetail")).mock(
        return_value=httpx.Response(
            200, json={"OrderStatus": [{"ERPOrderNumber": "0000000001", "LineStatusCode": "SCH"}]}
        )
    )
    result = client.shipping.shipment_detail(order_number="0000000001")
    assert result.order_status[0].erp_order_number == "0000000001"
    assert result.order_tracking == []


def test_shipping_serials_helper(client, config, respx_mock):
    route = respx_mock.post(_url(config, "shipping/ShipmentDetail")).mock(
        return_value=httpx.Response(
            200,
            json={"mT_OrderTrack_Response": {"OrderSerialNum": [
                {"ERPOrderLineNumber": "000020", "ManufSerialNo": "S440X", "MACAddress": "AA:BB:CC"}]}},
        )
    )
    serials = client.shipping.serials(order_number="59XXXX")
    assert _body(route)["mT_OrderTrack_API_Req"]["serialData"] == "Y"
    assert len(serials) == 1
    assert serials[0].manuf_serial_no == "S440X"
    assert serials[0].mac_address == "AA:BB:CC"


def test_account_detail(client, config, respx_mock):
    respx_mock.post(_url(config, "accountdetail/getaccountdetail")).mock(
        return_value=httpx.Response(
            200,
            json={
                "mT_AccountDetail_S_Resp": {
                    "customerDetails": {"name": "Tech Co", "countryKey": "NL"},
                    "contactDetails": [{"fullName": "Recv Dept", "eMail": "a@b.com"}],
                }
            },
        )
    )
    result = client.accounts.detail(customer="0011223")
    assert result.customer_details.name == "Tech Co"
    assert result.customer_details.country_key == "NL"
    assert result.contact_details[0].email == "a@b.com"  # eMail alias


def test_account_search_casing(client, config, respx_mock):
    respx_mock.post(_url(config, "accountsearch/getaccounts")).mock(
        return_value=httpx.Response(
            200,
            json={
                "mT_AccountSearch_S_Resp": {
                    "TotalCount": 1,
                    "CustomerDetails": [{"customer": "0011223", "name1": "Tech Co"}],
                }
            },
        )
    )
    result = client.accounts.search(name="Tech")
    # TotalCount/CustomerDetails PascalCase accepted.
    assert result.total_count == "1"
    assert result.customer_details[0].name1 == "Tech Co"


def test_order_status_value(client, config, respx_mock):
    route = respx_mock.post(_url(config, "orderstatusvalue/getorderstatusvalue")).mock(
        return_value=httpx.Response(
            200,
            json={
                "mT_OrderStatusValue_Response": {
                    "orderStatus": [{"eRPOrderNumber": "0001", "lineStatusCode": "REJ"}],
                    "orderValue": [{"eRPOrderNumber": "0001", "value": "148.67", "currency": "USD"}],
                }
            },
        )
    )
    result = client.orders.status_value(["000001", "000002"])
    sent = _body(route)["mT_OrderStatusValue_API_REQ"]
    assert sent["order"] == ["000001", "000002"]
    assert sent["order_type"] == "W"
    assert result.order_status[0].erp_order_number == "0001"
    assert result.order_value[0].value == "148.67"
