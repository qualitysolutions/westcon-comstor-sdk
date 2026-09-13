"""Misc / outlier resources: AEM Secure Content."""

from __future__ import annotations

from typing import Any, Mapping

from .. import _endpoints as ep
from ._base import AsyncResource, SyncResource


class AemResource(SyncResource):
    def order_now(self, payload: Mapping[str, Any]) -> Any:
        """Submit an AEM Secure Content access request.

        This endpoint's request body is a free-form ServiceNow-style catalog request
        (``sysparm_quantity`` + ``variables``); it returns no documented body.
        """
        return self._t.request("POST", ep.PATH_AEM_SECURE_CONTENT, json=dict(payload))


class AsyncAemResource(AsyncResource):
    async def order_now(self, payload: Mapping[str, Any]) -> Any:
        return await self._t.request("POST", ep.PATH_AEM_SECURE_CONTENT, json=dict(payload))
