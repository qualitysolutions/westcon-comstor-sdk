"""Models for the Carrier Tracking and Shipment Detail APIs."""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from .common import WestconModel

# ---------------------------------------------------------------------------
# Carrier Tracking (ShipmentTracking / ShipmentTrackingResponse) - camelCase
# ---------------------------------------------------------------------------


class TrackingImage(WestconModel):
    image: Optional[str] = None
    image_date: Optional[str] = None
    image_type: Optional[str] = None


class ServiceEvent(WestconModel):
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    event_location: Optional[str] = None
    event_description: Optional[str] = None


class ShipmentTrackingResult(WestconModel):
    order_number: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipment_date: Optional[str] = None
    pieces: Optional[str] = None
    weight: Optional[str] = None
    weight_unit: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    delivery_date: Optional[str] = None
    signature: Optional[str] = None
    #: Base64-encoded proof-of-delivery signature image.
    signature_image: Optional[str] = None
    signature_image_type: Optional[str] = None
    additional_images: List[TrackingImage] = []
    service_events: List[ServiceEvent] = []
    error_code: Optional[str] = None
    error_description: Optional[str] = None


# ---------------------------------------------------------------------------
# Shipment Detail (MT_OrderTrack_API_Req / MT_OrderTrack_Response) - PascalCase
# ---------------------------------------------------------------------------


class OrderStatusDetail(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="ERPOrderNumber")
    erp_order_line_number: Optional[str] = Field(default=None, alias="ERPOrderLineNumber")
    customer_order_number: Optional[str] = Field(default=None, alias="CustomerOrderNumber")
    customer_long_po_number: Optional[str] = Field(default=None, alias="CustomerLongPONumber")
    customer_line_number: Optional[str] = Field(default=None, alias="CustomerLineNumber")
    erp_product_number: Optional[str] = Field(default=None, alias="ERPProductNumber")
    line_quantity: Optional[str] = Field(default=None, alias="LineQuantity")
    unit_of_measure: Optional[str] = Field(default=None, alias="UnitOfMeasure")
    line_status_code: Optional[str] = Field(default=None, alias="LineStatusCode")
    line_status_description: Optional[str] = Field(default=None, alias="LineStatusDescription")
    status_date: Optional[str] = Field(default=None, alias="StatusDate")
    ship_date: Optional[str] = Field(default=None, alias="ShipDate")
    estimated_ship_date: Optional[str] = Field(default=None, alias="EstimatedShipDate")
    estimated_delivery_date: Optional[str] = Field(default=None, alias="estimatedDeliveryDate")
    billing_document: Optional[str] = Field(default=None, alias="BillingDocument")
    parent_erp_line: Optional[str] = Field(default=None, alias="ParentERPLine")
    vendor_sales_order_number: Optional[str] = Field(default=None, alias="VendorSalesOrderNumber")


class OrderTrackingDetail(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="ERPOrderNumber")
    erp_order_line_number: Optional[str] = Field(default=None, alias="ERPOrderLineNumber")
    customer_order_number: Optional[str] = Field(default=None, alias="CustomerOrderNumber")
    customer_long_po_number: Optional[str] = Field(default=None, alias="CustomerLongPONumber")
    customer_line_number: Optional[str] = Field(default=None, alias="CustomerLineNumber")
    parent_erp_line: Optional[str] = Field(default=None, alias="ParentERPLine")
    line_quantity: Optional[str] = Field(default=None, alias="LineQuantity")
    unit_of_measure: Optional[str] = Field(default=None, alias="UnitOfMeasure")
    ship_date: Optional[str] = Field(default=None, alias="ShipDate")
    tracking_no: Optional[str] = Field(default=None, alias="TrackingNo")
    carrier: Optional[str] = Field(default=None, alias="Carrier")


class OrderSerialNumber(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="ERPOrderNumber")
    erp_order_line_number: Optional[str] = Field(default=None, alias="ERPOrderLineNumber")
    customer_order_number: Optional[str] = Field(default=None, alias="CustomerOrderNumber")
    customer_long_po_number: Optional[str] = Field(default=None, alias="CustomerLongPONumber")
    customer_line_number: Optional[str] = Field(default=None, alias="CustomerLineNumber")
    parent_erp_line: Optional[str] = Field(default=None, alias="ParentERPLine")
    manuf_serial_no: Optional[str] = Field(default=None, alias="ManufSerialNo")
    mac_address: Optional[str] = Field(default=None, alias="MACAddress")
    tracking_no: Optional[str] = Field(default=None, alias="TrackingNo")


class OrderVRFData(WestconModel):
    erp_order_number: Optional[str] = Field(default=None, alias="ERPOrderNumber")
    erp_order_line_number: Optional[str] = Field(default=None, alias="ERPOrderLineNumber")
    customer_order_number: Optional[str] = Field(default=None, alias="CustomerOrderNumber")
    customer_long_po_number: Optional[str] = Field(default=None, alias="CustomerLongPONumber")
    customer_line_number: Optional[str] = Field(default=None, alias="CustomerLineNumber")
    parent_erp_line: Optional[str] = Field(default=None, alias="ParentERPLine")
    name: Optional[str] = Field(default=None, alias="Name")
    value: Optional[str] = Field(default=None, alias="Value")


class OrderTrackResult(WestconModel):
    """Inner payload of ``MT_OrderTrack_Response``."""

    order_status: List[OrderStatusDetail] = Field(default=[], alias="OrderStatus")
    order_tracking: List[OrderTrackingDetail] = Field(default=[], alias="OrderTracking")
    order_serial_num: List[OrderSerialNumber] = Field(default=[], alias="OrderSerialNum")
    order_vrf_data: List[OrderVRFData] = Field(default=[], alias="OrderVRFData")
