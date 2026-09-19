"""Base model and shared data types used across Westcon-Comstor APIs."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import AliasChoices, AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_pascal

# The three date shapes Comstor actually returns across its APIs.
_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")        # 2026-08-07
_COMPACT_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")      # 20260807 (Event Listener)
_SLASH_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")  # 25/09/2026 or 09/25/2026


def _as_date(y: int, mo: int, d: int) -> Optional[date]:
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def to_comstor_date(raw: Optional[str], dayfirst: bool = True) -> Optional[date]:
    """Best-effort parse of ANY Comstor date string to a :class:`datetime.date`.

    Comstor returns dates in three shapes across its APIs:

    * ISO ``YYYY-MM-DD`` and compact ``YYYYMMDD`` - unambiguous; parsed as-is.
    * slash ``D/M/YYYY`` - the day/month order varies by endpoint. When one part is
      > 12 it can only be the day, so the order is auto-detected; only when BOTH parts
      are <= 12 is the value genuinely ambiguous, and ``dayfirst`` decides (Comstor's
      European quote dates are day-first; US-format VRF licence dates are month-first).

    Unlike ``dateutil.parser`` this never applies ``dayfirst`` to ISO/compact dates,
    never fuzzy-fills missing components, and returns ``None`` (never raises) for any
    shape it does not recognise - so malformed data surfaces instead of being coerced.
    Call ``.isoformat()`` on the result for an ISO string.
    """
    s = (raw or "").strip()
    if not s:
        return None
    m = _ISO_DATE_RE.match(s) or _COMPACT_DATE_RE.match(s)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        return _as_date(y, mo, d)
    m = _SLASH_DATE_RE.match(s)
    if m:
        a, b, y = (int(g) for g in m.groups())
        if a > 12 >= b:        # first part can only be the day
            d, mo = a, b
        elif b > 12 >= a:      # second part can only be the day
            mo, d = a, b
        else:                  # ambiguous (both <= 12) or both invalid -> honour the hint
            d, mo = (a, b) if dayfirst else (b, a)
        return _as_date(y, mo, d)
    return None


def _validation_aliases(field_name: str) -> AliasChoices:
    """Accept both camelCase and PascalCase for a field on input.

    Westcon payloads are inconsistent: the same concept appears as ``openOrderList`` in
    one API's docs and ``OpenOrderList`` in the live response. Accepting both (plus the
    snake_case name via ``populate_by_name``) means we don't silently drop data over a
    capitalised first letter.
    """
    return AliasChoices(to_camel(field_name), to_pascal(field_name))


class WestconModel(BaseModel):
    """Base for all SDK models.

    * The alias generator accepts both ``camelCase`` and ``PascalCase`` JSON keys on
      input, and serialises to ``camelCase``.
    * ``populate_by_name`` lets callers construct models with the snake_case name.
    * ``extra="allow"`` keeps unknown keys, so we never drop data we did not model.

    Fields whose live key is irregular (``eRPOrderNumber``, ``customerPONumber``, ...)
    still override with an explicit ``Field(alias=...)``.
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=_validation_aliases,
            serialization_alias=to_camel,
        ),
        populate_by_name=True,
        extra="allow",
        protected_namespaces=(),
    )


class ErrorPair(WestconModel):
    """Common ``{error, errorDescription}`` error object (order/invoice lists)."""

    error: Optional[str] = None
    error_description: Optional[str] = None


class ErrorNumberPair(WestconModel):
    """Common ``{errorNumber, errorDescription}`` error object (availability/pricing)."""

    error_number: Optional[str] = None
    error_description: Optional[str] = None


class Price(WestconModel):
    """Monetary value as returned by the quoting APIs."""

    currency_iso: Optional[str] = None
    formatted_value: Optional[str] = None
    value: Optional[float] = None
    value_without_currency: Optional[str] = None


class Country(WestconModel):
    isocode: Optional[str] = None
    name: Optional[str] = None


class Region(WestconModel):
    isocode: Optional[str] = None
    isocode_short: Optional[str] = None
    name: Optional[str] = None
    country_iso: Optional[str] = None


class Account(WestconModel):
    """Account/party block used by the quoting APIs."""

    account_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    address_line4: Optional[str] = None
    locality: Optional[str] = None
    district: Optional[str] = None
    town: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[Country] = None


class Address(WestconModel):
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    formatted_address: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    line4: Optional[str] = None
    phone: Optional[str] = None
    town: Optional[str] = None
    postal_code: Optional[str] = None
    region: Optional[Region] = None
    country: Optional[Country] = None
