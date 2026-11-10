"""Models for the Order Status Event Listener API (OrderStatusMessages / ...Confirm)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import AliasChoices, Field, field_validator

from .common import WestconModel

#: Synthetic events that carry no order data (batchID 0). The live API also sends an EMPTY
#: eventType as its idle response (confirmed by Comstor), which the spec does not document.
CONTROL_EVENT_TYPES = frozenset({"RECONNECT", "NODATA", ""})


class OrderStatusEvent(WestconModel):
    """One order line-status event.

    The spec documents ``ORDER_UPDATED`` but the live UAT feed sends ``ORDER_CHANGED``
    (verified 2026-11-10), so use :attr:`is_order_event` rather than comparing
    ``event_type`` yourself.
    """

    erp_order_number: Optional[str] = Field(default=None, alias="eRPOrderNumber")
    customer_order_number: Optional[str] = None
    erp_order_line_number: Optional[str] = Field(default=None, alias="eRPOrderLineNumber")
    customer_line_number: Optional[str] = None
    line_status_code: Optional[str] = None
    line_status_description: Optional[str] = None
    event_type: Optional[str] = None
    event_description: Optional[str] = None
    #: ``YYYY-MM-DDTHH:MM:SS`` without a time zone (UAT suggests US Eastern; unconfirmed).
    event_date: Optional[str] = None
    status: Optional[str] = None
    status_description: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return (self.event_type or "").strip().upper() == "ERROR"

    @property
    def is_control(self) -> bool:
        """An idle/control message (RECONNECT, NODATA or empty eventType), not an order event."""
        return (self.event_type or "").strip().upper() in CONTROL_EVENT_TYPES

    @property
    def is_order_event(self) -> bool:
        """A real order event: it carries an order number and is not an error/control message.

        Keyed off the order number rather than one event-type string, so ``ORDER_UPDATED``
        (spec), ``ORDER_CHANGED`` (live) and any future order event type all qualify.
        """
        return bool((self.erp_order_number or "").strip()) and not (self.is_error or self.is_control)

    @property
    def event_datetime(self) -> Optional[datetime]:
        """``event_date`` as a naive :class:`datetime` (time zone unspecified), or ``None``."""
        try:
            return datetime.fromisoformat((self.event_date or "").strip())
        except ValueError:
            return None

    @property
    def line_key(self) -> tuple[str, str]:
        """``(order number, line number)`` with the line zero-padded to the live 6-char form.

        The spec's sample shows ``"10"``; the live feed sends ``"000010"``.
        """
        return (
            (self.erp_order_number or "").strip(),
            (self.erp_order_line_number or "").strip().zfill(6),
        )


class OrderStatusEventBatch(WestconModel):
    """Inner payload of ``getOrderStatusMessageResponse.getOrderStatusMessageResult``.

    Confirm a batch with ``client.order_events.confirm(batch.batch_id)`` once processed.
    A ``batch_id`` of 0 (idle/control response) has nothing to confirm.
    """

    batch_id: int = Field(
        default=0,
        validation_alias=AliasChoices("batchID", "batchId", "BatchID"),
        serialization_alias="batchID",
    )
    total_events: int = 0
    events: List[OrderStatusEvent] = []

    @field_validator("batch_id", "total_events", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None or v == "" else v

    @field_validator("events", mode="before")
    @classmethod
    def _single_event_to_list(cls, v: Any) -> Any:
        return [v] if isinstance(v, dict) else v

    @property
    def order_events(self) -> List[OrderStatusEvent]:
        return [e for e in self.events if e.is_order_event]

    @property
    def errors(self) -> List[OrderStatusEvent]:
        return [e for e in self.events if e.is_error]

    def latest_per_line(self) -> List[OrderStatusEvent]:
        """The most recent order event per order line, in first-seen order.

        The live feed can deliver the same order/line several times in one batch (UAT,
        2026-11-10: every line twice, ~45 min apart). Ties and unparseable dates keep the
        later event in the batch.
        """
        latest: dict[tuple[str, str], OrderStatusEvent] = {}
        for event in self.order_events:
            key = event.line_key
            current = latest.get(key)
            if current is None:
                latest[key] = event
                continue
            new_at, cur_at = event.event_datetime, current.event_datetime
            if new_at is None or cur_at is None or new_at >= cur_at:
                latest[key] = event
        return list(latest.values())


class OrderEventConfirmResult(WestconModel):
    """Response of OrderStatusMessagesConfirm: ``{"status": "200", "statusDescription": ...}``."""

    status: Optional[str] = None
    status_description: Optional[str] = None

    @property
    def ok(self) -> bool:
        """True unless the body reports a non-200 status (HTTP errors already raise)."""
        return self.status is None or self.status.strip() in ("", "200")
