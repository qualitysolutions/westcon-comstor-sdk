"""Orders resources: Open Order List, Order Status, Order Status Value."""

from __future__ import annotations

from typing import List, Mapping, Sequence, Union

from .. import _endpoints as ep
from ..models.orders import (
    OpenOrderListResult,
    OrderInvoice,
    OrderNumberQuery,
    OrderStatusLine,
    OrderStatusValueResult,
)
from ._base import AsyncResource, SyncResource

OrderItem = Union[str, OrderNumberQuery, Mapping[str, object]]


def _group_by_invoice(lines: List[OrderStatusLine]) -> List[OrderInvoice]:
    """Group invoiced lines by billing document, preserving first-seen order."""
    groups: dict[str | None, OrderInvoice] = {}
    ordered: List[OrderInvoice] = []
    for line in lines:
        key = line.billing_document
        group = groups.get(key)
        if group is None:
            group = OrderInvoice(invoice_number=key, lines=[])
            groups[key] = group
            ordered.append(group)
        group.lines.append(line)
    return ordered


class OrdersResource(SyncResource):
    def open_order_list(
        self,
        *,
        start_date: str,
        end_date: str | None = None,
        partner_key: str | None = None,
    ) -> OpenOrderListResult:
        """List active/unfulfilled orders between two ``YYYYMMDD`` dates."""
        payload = ep.build_open_order_list(self._partner_key(partner_key), start_date, end_date)
        raw = self._t.request("POST", ep.PATH_OPEN_ORDER_LIST, json=payload)
        return ep.parse_open_order_list(raw)

    def status(
        self,
        order: Sequence[OrderItem],
        *,
        order_type: str = "W",
        language: str = "EN",
        secondary_vrf_reference_field: str | None = None,
        secondary_vrf_reference_value: str | None = None,
        partner_key: str | None = None,
    ) -> List[OrderStatusLine]:
        """Return per-line status for one or more orders.

        ``order`` may be plain order-number strings (as in the portal example) or
        :class:`OrderNumberQuery` objects. ``order_type`` is ``"W"`` (Westcon sales
        order) or ``"C"`` (customer PO).
        """
        payload = ep.build_order_status(
            self._partner_key(partner_key),
            order,
            order_type,
            language,
            secondary_vrf_reference_field,
            secondary_vrf_reference_value,
        )
        raw = self._t.request("POST", ep.PATH_ORDER_STATUS, json=payload)
        return ep.parse_order_status(raw)

    def status_value(
        self,
        order: Sequence[str],
        *,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> OrderStatusValueResult:
        """Return order status plus order value (URUP Order Status Value API)."""
        payload = ep.build_order_status_value(
            self._partner_key(partner_key), order, order_type, language
        )
        raw = self._t.request("POST", ep.PATH_ORDER_STATUS_VALUE, json=payload)
        return ep.parse_order_status_value(raw)

    def invoiced_lines(
        self,
        order_number: str,
        *,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> List[OrderStatusLine]:
        """Return the invoiced (``INV``) lines of an order.

        Each line carries its invoice number in ``billing_document`` (an order can span
        several invoices) plus product, quantity and dates. Group by ``billing_document``
        to reconstruct each invoice. Note: lines carry no monetary amounts (those live on
        the Open Invoice List header) and no serial numbers.
        """
        lines = self.status(
            [order_number], order_type=order_type, language=language, partner_key=partner_key
        )
        return [line for line in lines if (line.line_status_code or "").upper() == "INV"]

    def invoices(
        self,
        order_number: str,
        *,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> List[OrderInvoice]:
        """Return the order's invoiced lines grouped by invoice (billing document).

        One order can span several invoices; each :class:`OrderInvoice` has the
        ``invoice_number`` and its ``lines``.
        """
        lines = self.invoiced_lines(
            order_number, order_type=order_type, language=language, partner_key=partner_key
        )
        return _group_by_invoice(lines)


class AsyncOrdersResource(AsyncResource):
    async def open_order_list(
        self,
        *,
        start_date: str,
        end_date: str | None = None,
        partner_key: str | None = None,
    ) -> OpenOrderListResult:
        payload = ep.build_open_order_list(self._partner_key(partner_key), start_date, end_date)
        raw = await self._t.request("POST", ep.PATH_OPEN_ORDER_LIST, json=payload)
        return ep.parse_open_order_list(raw)

    async def status(
        self,
        order: Sequence[OrderItem],
        *,
        order_type: str = "W",
        language: str = "EN",
        secondary_vrf_reference_field: str | None = None,
        secondary_vrf_reference_value: str | None = None,
        partner_key: str | None = None,
    ) -> List[OrderStatusLine]:
        payload = ep.build_order_status(
            self._partner_key(partner_key),
            order,
            order_type,
            language,
            secondary_vrf_reference_field,
            secondary_vrf_reference_value,
        )
        raw = await self._t.request("POST", ep.PATH_ORDER_STATUS, json=payload)
        return ep.parse_order_status(raw)

    async def status_value(
        self,
        order: Sequence[str],
        *,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> OrderStatusValueResult:
        payload = ep.build_order_status_value(
            self._partner_key(partner_key), order, order_type, language
        )
        raw = await self._t.request("POST", ep.PATH_ORDER_STATUS_VALUE, json=payload)
        return ep.parse_order_status_value(raw)

    async def invoiced_lines(
        self,
        order_number: str,
        *,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> List[OrderStatusLine]:
        lines = await self.status(
            [order_number], order_type=order_type, language=language, partner_key=partner_key
        )
        return [line for line in lines if (line.line_status_code or "").upper() == "INV"]

    async def invoices(
        self,
        order_number: str,
        *,
        order_type: str = "W",
        language: str = "EN",
        partner_key: str | None = None,
    ) -> List[OrderInvoice]:
        lines = await self.invoiced_lines(
            order_number, order_type=order_type, language=language, partner_key=partner_key
        )
        return _group_by_invoice(lines)
