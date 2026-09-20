"""Endpoint paths, request-payload builders and response parsers.

These pure functions hold all the per-operation knowledge (envelope keys, field
mapping) and are shared by the synchronous and asynchronous resource classes so the
two clients never drift apart.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Sequence, Union

from .models.accounts import AccountDetailResult, AccountSearchResult
from .models.invoices import InvoiceListResult
from .models.orders import (
    OpenOrderListResult,
    OrderNumberQuery,
    OrderStatusLine,
    OrderStatusValueResult,
)
from .models.products import AvailabilityProduct, PricingResult, ProductRef
from .models.quoting import GetQuoteResult
from .models.shipping import OrderTrackResult, ShipmentTrackingResult

# --- Endpoint paths (relative to Config.gateway_base_url) --------------------
PATH_OPEN_INVOICE_LIST = "OpenInvoiceList/GetList"
PATH_OPEN_ORDER_LIST = "OpenOrders/GetList"
PATH_ORDER_STATUS = "Orders/orderStatus"
PATH_AVAILABILITY = "api/products/availability"
PATH_PRICING = "Pricing/RetrievePrice"
PATH_GET_QUOTE = "QuoteDetail/retrieve"
PATH_CARRIER_TRACKING = "CarrierTracking/GetTrackingInfo"
PATH_SHIPMENT_DETAIL = "shipping/ShipmentDetail"
PATH_ACCOUNT_DETAIL = "accountdetail/getaccountdetail"
PATH_ACCOUNT_SEARCH = "accountsearch/getaccounts"
PATH_ORDER_STATUS_VALUE = "orderstatusvalue/getorderstatusvalue"
PATH_AEM_SECURE_CONTENT = "aem-secure-content/order_now"

ProductLike = Union[ProductRef, Mapping[str, Any]]


def _product_dict(product: ProductLike) -> dict[str, Any]:
    # Normalise both ProductRef and plain dicts (snake_ or camelCase keys) to the
    # camelCase JSON the API expects.
    ref = product if isinstance(product, ProductRef) else ProductRef.model_validate(dict(product))
    return ref.model_dump(by_alias=True, exclude_none=True)


def _unwrap(raw: Any, *candidate_keys: str) -> Any:
    """Return the inner value from an enveloped response.

    Matches ``candidate_keys`` case-insensitively and returns that value; otherwise
    returns ``raw`` unchanged (some live responses omit the documented envelope and are
    already the inner object). We deliberately do NOT unwrap an arbitrary single-key dict
    -- a payload like ``{"OrderStatus": [...]}`` is the inner object, not an envelope.
    """
    if isinstance(raw, dict):
        lowered = {k.lower(): k for k in raw}
        for key in candidate_keys:
            actual = lowered.get(key.lower())
            if actual is not None:
                return raw[actual]
    return raw


# --- Open Invoice List -------------------------------------------------------
def build_open_invoice_list(partner_key: str, start_date: str, end_date: str | None) -> dict[str, Any]:
    inner: dict[str, Any] = {"partnerKey": partner_key, "startDate": start_date}
    if end_date is not None:
        inner["endDate"] = end_date
    return {"mT_InvoiceList_S_Req": inner}


def parse_open_invoice_list(raw: Any) -> InvoiceListResult:
    return InvoiceListResult.model_validate(_unwrap(raw, "mT_InvoiceList_S_Resp"))


# --- Open Order List ---------------------------------------------------------
def build_open_order_list(partner_key: str, start_date: str, end_date: str | None) -> dict[str, Any]:
    inner: dict[str, Any] = {"partnerKey": partner_key, "startDate": start_date}
    if end_date is not None:
        inner["endDate"] = end_date
    return {"mT_OpenOrderList_Req": inner}


def parse_open_order_list(raw: Any) -> OpenOrderListResult:
    return OpenOrderListResult.model_validate(_unwrap(raw, "mT_OpenOrderList_S_Resp"))


# --- Order Status ------------------------------------------------------------
def build_order_status(
    partner_key: str,
    order: Sequence[Union[str, OrderNumberQuery, Mapping[str, Any]]],
    order_type: str,
    language: str,
    secondary_vrf_reference_field: str | None,
    secondary_vrf_reference_value: str | None,
) -> dict[str, Any]:
    order_payload: list[Any] = []
    for item in order:
        if isinstance(item, str):
            order_payload.append(item)
        elif isinstance(item, OrderNumberQuery):
            order_payload.append(item.model_dump(by_alias=True, exclude_none=True))
        else:
            order_payload.append(dict(item))
    inner: dict[str, Any] = {
        "partnerKey": partner_key,
        "orderType": order_type,
        "language": language,
        "order": order_payload,
    }
    if secondary_vrf_reference_field is not None:
        inner["secondaryVRFReferenceField"] = secondary_vrf_reference_field
    if secondary_vrf_reference_value is not None:
        inner["secondaryVRFReferenceValue"] = secondary_vrf_reference_value
    return {"mT_OrderStatus_API_REQ": inner}


def parse_order_status(raw: Any) -> List[OrderStatusLine]:
    inner = _unwrap(raw, "MT_OrderStatus_Response", "mT_OrderStatus_Response")
    if inner is None:
        return []
    if not isinstance(inner, list):
        inner = [inner]
    return [OrderStatusLine.model_validate(item) for item in inner]


# --- Availability ------------------------------------------------------------
def build_availability(
    partner_key: str, country_code: str, products: Sequence[ProductLike]
) -> dict[str, Any]:
    return {
        "Availability_Request": {
            "partnerKey": partner_key,
            "countryCode": country_code,
            "products": [_product_dict(p) for p in products],
        }
    }


def parse_availability(raw: Any) -> List[AvailabilityProduct]:
    inner = _unwrap(raw, "Availability_Response")
    if inner is None:
        return []
    if not isinstance(inner, list):
        inner = [inner]
    return [AvailabilityProduct.model_validate(item) for item in inner]


# --- Pricing -----------------------------------------------------------------
def build_pricing(
    partner_key: str,
    country_code: str,
    customer_price: str,
    currency: str,
    products: Sequence[ProductLike],
) -> dict[str, Any]:
    return {
        "mT_Pricing_S_Req": {
            "pricing": {
                "partnerKey": partner_key,
                "countryCode": country_code,
                "customerPrice": customer_price,
                "currency": currency,
                "products": [_product_dict(p) for p in products],
            }
        }
    }


def parse_pricing(raw: Any) -> List[PricingResult]:
    inner = _unwrap(raw, "MT_Pricing_Resp", "mT_Pricing_Resp")
    if inner is None:
        return []
    if not isinstance(inner, list):
        inner = [inner]
    return [PricingResult.model_validate(item) for item in inner]


def prices_by_product(results: List[PricingResult], *, price_field: str = "list") -> dict[str, float]:
    """Map ``{productNumber: price}`` from Pricing results, skipping errored/zero rows.

    ``price_field`` is ``"list"`` (default) or ``"customer"``.
    """
    out: dict[str, float] = {}
    for row in results:
        if row.error and (row.error.error_number or row.error.error_description):
            continue
        product = row.product
        if not product or not product.product_number:
            continue
        value = product.list_price if price_field == "list" else product.customer_price
        if value:
            out[product.product_number] = float(value)
    return out


def normalize_products(products: Any) -> tuple[list[ProductLike], list[str]]:
    """Accept a str, a ProductRef/dict, or a sequence thereof.

    Returns ``(payload_items, requested_product_numbers)`` where each payload item is a
    ProductRef/dict suitable for a pricing request.
    """
    if isinstance(products, (str, ProductRef, Mapping)):
        products = [products]
    payload: list[ProductLike] = []
    numbers: list[str] = []
    for item in products:
        if isinstance(item, str):
            payload.append({"product_number": item})
            numbers.append(item)
        elif isinstance(item, ProductRef):
            payload.append(item)
            if item.product_number:
                numbers.append(item.product_number)
        else:  # Mapping
            payload.append(item)
            number = item.get("product_number") or item.get("productNumber")
            if number:
                numbers.append(str(number))
    return payload, numbers


# --- Get Quote ---------------------------------------------------------------
def build_get_quote(partner_key: str, reseller_id: str, quote_id: str, version: str) -> dict[str, Any]:
    # Flat body (not enveloped).
    return {
        "partnerKey": partner_key,
        "resellerId": reseller_id,
        "quoteId": quote_id,
        "version": version,
    }


def parse_get_quote(raw: Any) -> GetQuoteResult:
    return GetQuoteResult.model_validate(raw)


# --- Carrier Tracking --------------------------------------------------------
def build_carrier_tracking(
    partner_key: str, order_number: str, carrier: str, tracking_number: str
) -> dict[str, Any]:
    return {
        "shipmentTracking": {
            "mT_ShipmentTracking_API_Req": {
                "partnerKey": partner_key,
                "orderNumber": order_number,
                "carrier": carrier,
                "trackingNumber": tracking_number,
            }
        }
    }


def parse_carrier_tracking(raw: Any) -> ShipmentTrackingResult:
    outer = _unwrap(raw, "shipmentTrackingResponse")
    inner = _unwrap(outer, "shipmentTrackingResult")
    return ShipmentTrackingResult.model_validate(inner)


# --- Shipment Detail ---------------------------------------------------------
def build_shipment_detail(
    partner_key: str,
    order_number: str,
    order_type: str,
    language: str,
    tracking_data: str | None,
    serial_data: str | None,
    vrf_data: str | None,
    secondary_vrf_reference_field: str | None,
    secondary_vrf_reference_value: str | None,
) -> dict[str, Any]:
    inner: dict[str, Any] = {
        "partnerKey": partner_key,
        "orderType": order_type,
        "language": language,
        "orderNumber": order_number,
    }
    if tracking_data is not None:
        inner["trackingData"] = tracking_data
    if serial_data is not None:
        inner["serialData"] = serial_data
    if vrf_data is not None:
        inner["vrfData"] = vrf_data
    if secondary_vrf_reference_field is not None:
        inner["secondaryVRFReferenceField"] = secondary_vrf_reference_field
    if secondary_vrf_reference_value is not None:
        inner["secondaryVRFReferenceValue"] = secondary_vrf_reference_value
    return {"mT_OrderTrack_API_Req": inner}


def parse_shipment_detail(raw: Any) -> OrderTrackResult:
    return OrderTrackResult.model_validate(_unwrap(raw, "mT_OrderTrack_Response"))


# --- Account Detail ----------------------------------------------------------
def build_account_detail(partner_key: str, customer: str | None) -> dict[str, Any]:
    inner: dict[str, Any] = {"partnerKey": partner_key}
    if customer is not None:
        inner["customer"] = customer
    return {"mT_AccountDetail_S_Req": inner}


def parse_account_detail(raw: Any) -> AccountDetailResult:
    return AccountDetailResult.model_validate(_unwrap(raw, "mT_AccountDetail_S_Resp"))


# --- Account Search ----------------------------------------------------------
def build_account_search(
    partner_key: str, name: str | None, customer: str | None, country: str | None
) -> dict[str, Any]:
    inner: dict[str, Any] = {"partnerKey": partner_key}
    if name is not None:
        inner["name"] = name
    if customer is not None:
        inner["customer"] = customer
    if country is not None:
        inner["country"] = country
    return {"mT_AccountSearch_S_Req": inner}


def parse_account_search(raw: Any) -> AccountSearchResult:
    return AccountSearchResult.model_validate(_unwrap(raw, "mT_AccountSearch_S_Resp"))


# --- Order Status Value ------------------------------------------------------
def build_order_status_value(
    partner_key: str, order: Sequence[str], order_type: str, language: str
) -> dict[str, Any]:
    # The gateway validates this endpoint against the Order Status request contract:
    # it wants the ``mT_OrderStatus_API_REQ`` wrapper with camelCase ``orderType`` (the
    # ``mT_OrderStatusValue_API_REQ`` / ``order_type`` form is rejected with a 400
    # "Missing required fields: mt_orderstatus_api_req").
    return {
        "mT_OrderStatus_API_REQ": {
            "partnerKey": partner_key,
            "orderType": order_type,
            "language": language,
            "order": list(order),
        }
    }


def parse_order_status_value(raw: Any) -> OrderStatusValueResult:
    # Live responses come back as ``MT_OrderStatus_Response`` (a bare list of status
    # lines, no order-value block); the documented ``mT_OrderStatusValue_Response``
    # envelope with orderStatus/orderValue is also accepted.
    inner = _unwrap(raw, "mT_OrderStatusValue_Response", "MT_OrderStatus_Response")
    if isinstance(inner, list):
        inner = {"orderStatus": inner}
    return OrderStatusValueResult.model_validate(inner)
