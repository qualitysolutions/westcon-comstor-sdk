"""Models for Open Order List, Order Status and Order Status Value APIs."""

from __future__ import annotations

from typing import List, Optional

from pydantic import AliasChoices, Field

from .common import ErrorPair, WestconModel

# ---------------------------------------------------------------------------
# Open Order List (MT_OpenOrderList_Req / MT_OpenOrderList_S_Resp)
# ---------------------------------------------------------------------------


class OpenOrder(WestconModel):
    sales_order_number: Optional[str] = None
    order_date: Optional[str] = None
    customer_po_number: Optional[str] = Field(default=None, alias="customerPONumber")
    amount: Optional[str] = None
    currency: Optional[str] = None
    end_user_name: Optional[str] = None
    westcon_sales_org: Optional[str] = None
    country: Optional[str] = None


class OpenOrderListResult(WestconModel):
    """Inner payload of ``MT_OpenOrderList_S_Resp``."""

    open_order_list: List[OpenOrder] = []
    error: Optional[ErrorPair] = None


# ---------------------------------------------------------------------------
# Order Status (MT_OrderStatus_API_REQ / MT_OrderStatus_Response)
# ---------------------------------------------------------------------------


class OrderStatusLine(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="eRPOrderNumber")
    erp_order_line_number: Optional[str] = Field(default=None, alias="eRPOrderLineNumber")
    customer_order_number: Optional[str] = None
    customer_long_po_number: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("customerLongPONumber", "CustomerLongPONumber"),
        serialization_alias="customerLongPONumber",
    )
    customer_line_number: Optional[str] = None
    erp_product_number: Optional[str] = Field(default=None, alias="eRPProductNumber")
    line_quantity: Optional[str] = None
    unit_of_measure: Optional[str] = None
    line_status_code: Optional[str] = None
    line_status_description: Optional[str] = None
    status_date: Optional[str] = None
    estimated_ship_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("estimatedShipDate", "EstimatedShipDate"),
        serialization_alias="estimatedShipDate",
    )
    estimated_delivery_date: Optional[str] = None
    ship_date: Optional[str] = None
    billing_document: Optional[str] = None
    parent_erp_line: Optional[str] = Field(default=None, alias="parentERPLine")
    vendor_sales_order_number: Optional[str] = None


class OrderInvoice(WestconModel):
    """Invoiced lines of an order grouped under one invoice (billing document).

    ``invoice_number`` is the SAP billing document. ``lines`` carry product, quantity and
    dates but no monetary amounts (those live on the Open Invoice List header) and no
    serials.
    """

    invoice_number: Optional[str] = None
    lines: List["OrderStatusLine"] = []


class OrderNumberQuery(WestconModel):
    """One entry of the Order Status request ``order`` array.

    The Order Status example sends bare order-number strings, while the schema
    documents an object with ``orderNumber`` plus optional secondary VRF fields.
    Callers may pass either a string or this object; see the resource method.
    """

    order_number: Optional[str] = None
    secondary_vrf_reference_field: Optional[str] = None
    secondary_vrf_reference_value: Optional[str] = None


# ---------------------------------------------------------------------------
# Order Status Value (MT_OrderStatusValue_API_REQ / MT_OrderStatusValue_Response)
# ---------------------------------------------------------------------------


class OrderStatusValueLine(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="eRPOrderNumber")
    erp_order_line_number: Optional[str] = Field(default=None, alias="eRPOrderLineNumber")
    customer_order_number: Optional[str] = None
    customer_line_number: Optional[str] = None
    erp_product_number: Optional[str] = Field(default=None, alias="eRPProductNumber")
    line_quantity: Optional[str] = None
    unit_of_measure: Optional[str] = None
    line_status_code: Optional[str] = None
    line_status_description: Optional[str] = None
    status_date: Optional[str] = None
    ship_date: Optional[str] = None
    billing_document: Optional[str] = None
    parent_erp_line: Optional[str] = Field(default=None, alias="parentERPLine")


class OrderValue(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="eRPOrderNumber")
    customer_order_number: Optional[str] = None
    value: Optional[str] = None
    currency: Optional[str] = None


class OrderStatusValueResult(WestconModel):
    """Inner payload of ``MT_OrderStatusValue_Response``."""

    order_status: List[OrderStatusValueLine] = []
    order_value: List[OrderValue] = []
