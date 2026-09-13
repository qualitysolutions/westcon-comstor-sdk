"""Thorough read-only live check of the Westcon-Comstor API endpoints.

Exercises every implemented "get" endpoint and reports whether it returned well-formed,
expected data. Self-bootstrapping: the list endpoints (open orders/invoices, account
search) discover real identifiers that are then fed into the detail endpoints (order
status, shipment detail, carrier tracking, account detail).

READ-ONLY: never calls a "submit" endpoint. The AEM Secure Content endpoint (which places
a request) is deliberately NOT exercised.

Usage:
    # UAT:
    WESTCON_GATEWAY_BASE_URL=https://westconapiuat.azure-api.net \
        python examples/live_check.py --country SE CW9172I-RTG CW9171I-RTG
    # Prod: omit the env override (uses api.westconcomstor.com) with prod keys.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path
from typing import Any, Callable

from westcon_comstor import Config, WestconComstorClient
from westcon_comstor.errors import WestconComstorError

DEFAULT_SKUS = ["CW9172I-RTG", "CW9171I-RTG", "CW9174I-RTG", "C9200L-48P-4X-M"]

# ---- reporting -------------------------------------------------------------
PASS, PARTIAL, FAIL, SKIP = "PASS", "PARTIAL", "FAIL", "SKIP"
_results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str) -> None:
    _results.append((name, status, detail))
    print(f"[{status:7}] {name}: {detail}")


def check(name: str, fn: Callable[[], tuple[str, str]]) -> Any:
    """Run one check; fn returns (status, detail). Exceptions are caught and reported."""
    try:
        status, detail = fn()
    except WestconComstorError as exc:
        record(name, FAIL, f"{type(exc).__name__}: {exc}")
        return None
    except Exception as exc:  # noqa: BLE001 - diagnostic tool
        record(name, FAIL, f"unexpected {type(exc).__name__}: {exc}")
        return None
    record(name, status, detail)
    return None


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Live read-only check of Westcon-Comstor endpoints")
    ap.add_argument("skus", nargs="*", default=DEFAULT_SKUS, help="product numbers to price")
    ap.add_argument("--country", default="SE")
    ap.add_argument("--start", default=None, help="YYYYMMDD (default: 3 years ago)")
    ap.add_argument("--end", default=None, help="YYYYMMDD (default: today)")
    args = ap.parse_args()

    _load_dotenv()
    try:
        config = Config.from_env()
    except Exception as exc:
        print(f"Missing/invalid credentials: {exc}", file=sys.stderr)
        return 2

    today = _dt.date.today()
    start = args.start or (today.replace(year=today.year - 3)).strftime("%Y%m%d")
    end = args.end or today.strftime("%Y%m%d")
    skus = args.skus or DEFAULT_SKUS

    print(f"Gateway: {config.gateway_base_url}")
    print(f"Country: {args.country}   Date range: {start}..{end}   SKUs: {skus}\n")

    with WestconComstorClient(config) as c:
        # -- Product Information -------------------------------------------
        def _pricing() -> tuple[str, str]:
            res = c.products.pricing(country_code=args.country, currency="SEK", products=[
                {"product_number": s} for s in skus])
            priced = [r for r in res if r.product and r.product.list_price]
            if not priced:
                return PARTIAL, f"{len(res)} rows, none with a listPrice"
            sample = priced[0].product
            return PASS, (f"{len(priced)}/{len(skus)} priced; "
                          f"e.g. {sample.product_number}={sample.list_price} {sample.currency}")
        check("pricing", _pricing)

        def _availability() -> tuple[str, str]:
            res = c.products.availability(country_code=args.country, products=[
                {"product_number": s} for s in skus])
            with_stock = [p for p in res if p.storage_locations]
            errs = [p for p in res if p.error and (p.error.error_number or p.error.error_description)]
            if not res:
                return PARTIAL, "no product rows returned"
            detail = f"{len(res)} rows, {len(with_stock)} with storage locations, {len(errs)} errored"
            if with_stock:
                loc = with_stock[0].storage_locations[0]
                detail += f"; e.g. {with_stock[0].product_number} qty={loc.available_quantity} @ {loc.plant}"
            return (PASS if with_stock else PARTIAL), detail
        check("availability", _availability)

        # -- Orders & Invoices (list -> discover ids) ----------------------
        discovered_orders: list[str] = []
        discovered_customer: str | None = None

        def _open_orders() -> tuple[str, str]:
            res = c.orders.open_order_list(start_date=start, end_date=end)
            if res.error and (res.error.error or res.error.error_description):
                return PARTIAL, f"error: {res.error.error} {res.error.error_description}"
            for o in res.open_order_list:
                if o.sales_order_number:
                    discovered_orders.append(o.sales_order_number)
            n = len(res.open_order_list)
            if not n:
                return PARTIAL, "0 open orders in range (nothing to chain from)"
            o0 = res.open_order_list[0]
            return PASS, f"{n} open orders; e.g. {o0.sales_order_number} {o0.amount} {o0.currency}"
        check("open_order_list", _open_orders)

        def _open_invoices() -> tuple[str, str]:
            res = c.invoices.list(start_date=start, end_date=end)
            if res.error and (res.error.error or res.error.error_description):
                return PARTIAL, f"error: {res.error.error} {res.error.error_description}"
            n = len(res.invoice)
            if not n:
                return PARTIAL, "0 invoices in range"
            i0 = res.invoice[0]
            return PASS, f"{n} invoices; e.g. {i0.billing_document} {i0.total_value} {i0.currency}"
        check("open_invoice_list", _open_invoices)

        order_no = discovered_orders[0] if discovered_orders else None

        def _order_status() -> tuple[str, str]:
            if not order_no:
                return SKIP, "no order number discovered to query"
            lines = c.orders.status([order_no], order_type="W")
            if not lines:
                return PARTIAL, f"order {order_no}: 0 status lines"
            l0 = lines[0]
            return PASS, f"order {order_no}: {len(lines)} lines; line1 status={l0.line_status_code} {l0.line_status_description}"
        check("order_status", _order_status)

        def _order_status_value() -> tuple[str, str]:
            if not order_no:
                return SKIP, "no order number discovered to query"
            res = c.orders.status_value([order_no], order_type="W")
            ns, nv = len(res.order_status), len(res.order_value)
            if not ns and not nv:
                return PARTIAL, f"order {order_no}: empty status/value"
            val = res.order_value[0] if res.order_value else None
            extra = f"; value={val.value} {val.currency}" if val else ""
            return PASS, f"order {order_no}: {ns} status, {nv} value rows{extra}"
        check("order_status_value", _order_status_value)

        tracking_ref = {}

        def _shipment_detail() -> tuple[str, str]:
            if not order_no:
                return SKIP, "no order number discovered to query"
            res = c.shipping.shipment_detail(order_number=order_no, order_type="W",
                                             tracking_data="Y", serial_data="Y", vrf_data="Y")
            ns = len(res.order_status)
            nt = len(res.order_tracking)
            nse = len(res.order_serial_num)
            if res.order_tracking:
                t = res.order_tracking[0]
                if t.tracking_no and t.carrier:
                    tracking_ref["order"] = order_no
                    tracking_ref["carrier"] = t.carrier
                    tracking_ref["tracking"] = t.tracking_no
            if not (ns or nt or nse):
                return PARTIAL, f"order {order_no}: empty blocks"
            return PASS, f"order {order_no}: {ns} status, {nt} tracking, {nse} serial rows"
        check("shipment_detail", _shipment_detail)

        def _carrier_tracking() -> tuple[str, str]:
            if not tracking_ref:
                return SKIP, "no (order, carrier, tracking#) discovered from shipment_detail"
            res = c.shipping.carrier_tracking(
                order_number=tracking_ref["order"], carrier=tracking_ref["carrier"],
                tracking_number=tracking_ref["tracking"])
            ev = len(res.service_events)
            return PASS, (f"tracking {tracking_ref['tracking']} via {res.carrier}: "
                          f"status={res.error_code}, {ev} events, delivered={res.delivery_date}")
        check("carrier_tracking", _carrier_tracking)

        # -- URUP Accounts -------------------------------------------------
        def _account_search() -> tuple[str, str]:
            nonlocal discovered_customer
            res = c.accounts.search(country=args.country)
            n = len(res.customer_details)
            if not n:
                return PARTIAL, f"0 accounts for country={args.country}"
            for a in res.customer_details:
                if a.customer:
                    discovered_customer = a.customer
                    break
            a0 = res.customer_details[0]
            return PASS, f"{res.total_count or n} accounts; e.g. {a0.customer} {a0.name1} {a0.city}"
        check("account_search", _account_search)

        def _account_detail() -> tuple[str, str]:
            if not discovered_customer:
                return SKIP, "no customer number discovered from account_search"
            res = c.accounts.detail(customer=discovered_customer)
            cd = res.customer_details
            contacts = res.contact_details if isinstance(res.contact_details, list) else (
                [res.contact_details] if res.contact_details else [])
            if not cd:
                return PARTIAL, f"customer {discovered_customer}: no customerDetails"
            return PASS, (f"customer {discovered_customer}: name={cd.name!r} "
                          f"{cd.city} {cd.country_key}; {len(contacts)} contact(s)")
        check("account_detail", _account_detail)

        # -- Quoting -------------------------------------------------------
        def _get_quote() -> tuple[str, str]:
            # No quoteId is available without an Event Listener QUOTE_CREATED event.
            # Probe with a placeholder to confirm reachability + error handling.
            try:
                res = c.quotes.get(quote_id="0", reseller_id="0", version="0")
            except WestconComstorError as exc:
                return PARTIAL, f"reachable; business error as expected without a real quoteId: {exc}"
            ok = res.success
            return (PASS if ok else PARTIAL), f"success={ok} message={res.message!r}"
        check("get_quote", _get_quote)

    # -- summary -----------------------------------------------------------
    print("\n=== SUMMARY ===")
    counts: dict[str, int] = {}
    for _, status, _ in _results:
        counts[status] = counts.get(status, 0) + 1
    for name, status, _ in _results:
        print(f"  {status:7} {name}")
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    # exit non-zero only if something hard-failed
    return 1 if counts.get(FAIL) else 0


if __name__ == "__main__":
    raise SystemExit(main())
