"""Order Status Event Listener: long-poll order line-status events, then confirm the batch."""

from __future__ import annotations

from datetime import date
from typing import Sequence, Union

from .. import _endpoints as ep
from ..config import Config
from ..models.order_events import OrderEventConfirmResult, OrderStatusEventBatch
from ._base import AsyncResource, SyncResource

DateLike = Union[str, date, None]

#: Seconds added to the long-poll timeout for the HTTP read timeout, so the client never
#: gives up before Comstor closes the long poll.
_READ_TIMEOUT_MARGIN = 30.0


def _headers(config: Config) -> dict[str, str] | None:
    # The Order Status Event Listener is a separate APIM product with its own subscription key.
    if config.order_event_subscription_key:
        return {"Ocp-Apim-Subscription-Key": config.order_event_subscription_key}
    return None


class OrderEventsResource(SyncResource):
    def poll(
        self,
        *,
        timeout_seconds: int = 60,
        start_date: DateLike = None,
        end_date: DateLike = None,
        partner_key: str | None = None,
    ) -> OrderStatusEventBatch:
        """Long-poll for unconfirmed order line-status events.

        Blocks up to ``timeout_seconds`` (5..300) when there is nothing to deliver. Pass
        ``start_date``/``end_date`` (``YYYYMMDD`` or :class:`datetime.date`) to re-fetch
        events created in that period, including confirmed ones. Unconfirmed events are
        re-delivered on every poll, each time under a new ``batch_id``.
        """
        payload = ep.build_order_events_poll(
            self._partner_key(partner_key), timeout_seconds, start_date, end_date
        )
        raw = self._t.request(
            "POST", ep.PATH_ORDER_EVENTS, json=payload, headers=_headers(self._config),
            timeout=timeout_seconds + _READ_TIMEOUT_MARGIN,
        )
        return ep.parse_order_events(raw)

    def confirm(
        self,
        batch_id: int,
        *,
        order_numbers: Sequence[str] | None = None,
        partner_key: str | None = None,
    ) -> OrderEventConfirmResult:
        """Acknowledge a batch so its events are not re-delivered.

        Confirm the latest ``batch_id``: unconfirmed events are re-delivered under a new batchID
        on every poll and never expire. Pass ``order_numbers`` to acknowledge only those orders:
        all Westcon order numbers or all PO numbers, never mixed (Comstor answers 500). Comstor
        answers "Success" even for an unknown batchID, so ``ok`` only means it was not rejected.
        """
        payload = ep.build_order_events_confirm(self._partner_key(partner_key), batch_id, order_numbers)
        raw = self._t.request(
            "POST", ep.PATH_ORDER_EVENTS_CONFIRM, json=payload, headers=_headers(self._config)
        )
        return ep.parse_order_events_confirm(raw)


class AsyncOrderEventsResource(AsyncResource):
    async def poll(
        self,
        *,
        timeout_seconds: int = 60,
        start_date: DateLike = None,
        end_date: DateLike = None,
        partner_key: str | None = None,
    ) -> OrderStatusEventBatch:
        payload = ep.build_order_events_poll(
            self._partner_key(partner_key), timeout_seconds, start_date, end_date
        )
        raw = await self._t.request(
            "POST", ep.PATH_ORDER_EVENTS, json=payload, headers=_headers(self._config),
            timeout=timeout_seconds + _READ_TIMEOUT_MARGIN,
        )
        return ep.parse_order_events(raw)

    async def confirm(
        self,
        batch_id: int,
        *,
        order_numbers: Sequence[str] | None = None,
        partner_key: str | None = None,
    ) -> OrderEventConfirmResult:
        payload = ep.build_order_events_confirm(self._partner_key(partner_key), batch_id, order_numbers)
        raw = await self._t.request(
            "POST", ep.PATH_ORDER_EVENTS_CONFIRM, json=payload, headers=_headers(self._config)
        )
        return ep.parse_order_events_confirm(raw)
