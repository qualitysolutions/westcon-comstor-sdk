"""Live integration tests against the real Westcon-Comstor API (read-only).

Skipped by default (marked ``integration``). Run with::

    WESTCON_ENV=uat pytest -m integration

Credentials are read from ``WESTCON_*`` env vars or the repo-root ``.env``. These tests
never call a "submit" endpoint (no AEM order_now). They assert the SDK reaches each
endpoint and parses the response into the right type; they tolerate empty datasets and
the URUP subscription-scope 401 (skipping rather than failing) so they stay green across
environments.

Tune the fixtures with env vars:
    WESTCON_TEST_COUNTRY (default SE)
    WESTCON_TEST_SKUS    (comma-separated; default CW9172I-RTG,CW9171I-RTG)
    WESTCON_TEST_START / WESTCON_TEST_END (YYYYMMDD; default 20180101..20261231)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from westcon_comstor import Config, WestconComstorClient
from westcon_comstor.errors import UnauthorizedError, WestconComstorError
from westcon_comstor.models.accounts import AccountSearchResult
from westcon_comstor.models.invoices import InvoiceListResult
from westcon_comstor.models.orders import OpenOrderListResult, OrderStatusValueResult
from westcon_comstor.models.shipping import OrderTrackResult

pytestmark = pytest.mark.integration

COUNTRY = os.getenv("WESTCON_TEST_COUNTRY", "SE")
SKUS = [s for s in os.getenv("WESTCON_TEST_SKUS", "CW9172I-RTG,CW9171I-RTG").split(",") if s]
START = os.getenv("WESTCON_TEST_START", "20180101")
END = os.getenv("WESTCON_TEST_END", "20261231")


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@pytest.fixture(scope="module")
def live():
    _load_dotenv()
    try:
        config = Config.from_env()
    except Exception as exc:  # ConfigurationError when creds absent
        pytest.skip(f"live credentials not configured: {exc}")
    client = WestconComstorClient(config)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="module")
def open_orders(live) -> list:
    res = live.orders.open_order_list(start_date=START, end_date=END)
    return list(res.open_order_list)


# --- product info -----------------------------------------------------------
def test_pricing(live):
    res = live.products.pricing(country_code=COUNTRY, currency="SEK",
                                products=[{"product_number": s} for s in SKUS])
    assert isinstance(res, list)
    priced = [r for r in res if r.product and r.product.list_price]
    assert priced, f"expected at least one priced SKU among {SKUS}"


def test_availability(live):
    res = live.products.availability(country_code=COUNTRY,
                                     products=[{"product_number": s} for s in SKUS])
    assert isinstance(res, list) and res


def test_fx_implied_rate(live):
    r = live.fx.implied_rate(base="USD", quote="SEK", products=SKUS, country=COUNTRY)
    assert r.base_currency == "USD" and r.quote_currency == "SEK"
    assert r.rate and r.rate > 0, "expected a positive implied USD->SEK rate"


# --- orders & invoices ------------------------------------------------------
def test_open_order_list(live):
    res = live.orders.open_order_list(start_date=START, end_date=END)
    assert isinstance(res, OpenOrderListResult)


def test_open_invoice_list(live):
    res = live.invoices.list(start_date=START, end_date=END)
    assert isinstance(res, InvoiceListResult)  # data may be empty for the test partner


def test_order_status(live, open_orders):
    if not open_orders:
        pytest.skip("no open orders in this environment to query")
    lines = live.orders.status([open_orders[0].sales_order_number])
    assert isinstance(lines, list)


def test_order_status_value(live, open_orders):
    if not open_orders:
        pytest.skip("no open orders to query")
    try:
        res = live.orders.status_value([open_orders[0].sales_order_number])
    except UnauthorizedError:
        pytest.skip("URUP Order Status Value API not in this subscription")
    assert isinstance(res, OrderStatusValueResult)


def test_shipment_detail_and_serials(live, open_orders):
    if not open_orders:
        pytest.skip("no open orders to query")
    order = open_orders[0].sales_order_number
    res = live.shipping.shipment_detail(order_number=order, serial_data="Y", tracking_data="Y")
    assert isinstance(res, OrderTrackResult)
    serials = live.shipping.serials(order_number=order)
    assert isinstance(serials, list)  # often empty (drop-ship / licence orders)


# --- accounts (URUP - may be out of subscription) ---------------------------
def test_account_search(live):
    try:
        res = live.accounts.search(country=COUNTRY)
    except UnauthorizedError:
        pytest.skip("URUP Account Search API not in this subscription")
    assert isinstance(res, AccountSearchResult)


# --- quoting (reachability; no valid quoteId available) ---------------------
def test_get_quote_reachable(live):
    # A bogus quoteId should reach the backend and come back as a business error,
    # proving the endpoint + error handling work end to end.
    try:
        res = live.quotes.get(quote_id="0", reseller_id="0", version="0")
    except WestconComstorError:
        return  # expected: reachable, returned an error status
    assert res.success is not None
