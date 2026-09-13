"""Shipping resources: Carrier Tracking and Shipment Detail."""

from __future__ import annotations

from typing import List

from .. import _endpoints as ep
from ..models.shipping import OrderSerialNumber, OrderTrackResult, ShipmentTrackingResult
from ._base import AsyncResource, SyncResource


class ShippingResource(SyncResource):
    def carrier_tracking(
        self,
        *,
        order_number: str,
        carrier: str,
        tracking_number: str,
        partner_key: str | None = None,
    ) -> ShipmentTrackingResult:
        """Track a shipment by carrier + tracking number for a Westcon order."""
        payload = ep.build_carrier_tracking(
            self._partner_key(partner_key), order_number, carrier, tracking_number
        )
        raw = self._t.request("POST", ep.PATH_CARRIER_TRACKING, json=payload)
        return ep.parse_carrier_tracking(raw)

    def shipment_detail(
        self,
        *,
        order_number: str,
        order_type: str = "W",
        language: str = "EN",
        tracking_data: str | None = None,
        serial_data: str | None = None,
        vrf_data: str | None = None,
        secondary_vrf_reference_field: str | None = None,
        secondary_vrf_reference_value: str | None = None,
        partner_key: str | None = None,
    ) -> OrderTrackResult:
        """Return order status, tracking, serial numbers and VRF data for an order.

        The ``*_data`` flags (``"Y"``/``"N"``) select which optional blocks to include.
        """
        payload = ep.build_shipment_detail(
            self._partner_key(partner_key),
            order_number,
            order_type,
            language,
            tracking_data,
            serial_data,
            vrf_data,
            secondary_vrf_reference_field,
            secondary_vrf_reference_value,
        )
        raw = self._t.request("POST", ep.PATH_SHIPMENT_DETAIL, json=payload)
        return ep.parse_shipment_detail(raw)

    def serials(
        self,
        *,
        order_number: str,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> List[OrderSerialNumber]:
        """Return just the serial numbers / MAC addresses for an order.

        Convenience over :meth:`shipment_detail` with ``serial_data="Y"``. Note serials
        are only populated for hardware shipped from Westcon stock; drop-ship and
        non-tangible (licence) lines return no serials.
        """
        result = self.shipment_detail(
            order_number=order_number,
            order_type=order_type,
            language=language,
            serial_data="Y",
            partner_key=partner_key,
        )
        return result.order_serial_num


class AsyncShippingResource(AsyncResource):
    async def carrier_tracking(
        self,
        *,
        order_number: str,
        carrier: str,
        tracking_number: str,
        partner_key: str | None = None,
    ) -> ShipmentTrackingResult:
        payload = ep.build_carrier_tracking(
            self._partner_key(partner_key), order_number, carrier, tracking_number
        )
        raw = await self._t.request("POST", ep.PATH_CARRIER_TRACKING, json=payload)
        return ep.parse_carrier_tracking(raw)

    async def shipment_detail(
        self,
        *,
        order_number: str,
        order_type: str = "W",
        language: str = "EN",
        tracking_data: str | None = None,
        serial_data: str | None = None,
        vrf_data: str | None = None,
        secondary_vrf_reference_field: str | None = None,
        secondary_vrf_reference_value: str | None = None,
        partner_key: str | None = None,
    ) -> OrderTrackResult:
        payload = ep.build_shipment_detail(
            self._partner_key(partner_key),
            order_number,
            order_type,
            language,
            tracking_data,
            serial_data,
            vrf_data,
            secondary_vrf_reference_field,
            secondary_vrf_reference_value,
        )
        raw = await self._t.request("POST", ep.PATH_SHIPMENT_DETAIL, json=payload)
        return ep.parse_shipment_detail(raw)

    async def serials(
        self,
        *,
        order_number: str,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> List[OrderSerialNumber]:
        result = await self.shipment_detail(
            order_number=order_number,
            order_type=order_type,
            language=language,
            serial_data="Y",
            partner_key=partner_key,
        )
        return result.order_serial_num
