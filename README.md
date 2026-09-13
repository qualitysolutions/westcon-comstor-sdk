# qls-westcon-comstor

Python SDK for the **Westcon-Comstor AIM** (API Integration Management) APIs. Sync and
async clients, typed request/response models (pydantic v2), OAuth2 handling and a
consistent error hierarchy.

> Status: **Phase 1** — authentication + the 12 core transactional APIs are implemented
> and tested. PartnerView is reachable today via the generic `client.request(...)`
> escape hatch and will get typed wrappers next (Phase 2, pending its spec).

## Install

```bash
pip install qls-westcon-comstor    # from PyPI
# or, from a checkout of this repo:
# pip install -e .
```

The distribution is `qls-westcon-comstor`; the import package is `westcon_comstor`.

Requires Python 3.10+. Depends on `httpx` and `pydantic>=2`.

## Authentication

All transactional APIs use the **OAuth 2.0 client-credentials** flow against Azure AD
(v1 token endpoint) and an APIM subscription key. Westcon-Comstor issues these values by
email when your partner account is provisioned:

| Value              | Where it goes                          |
| ------------------ | -------------------------------------- |
| `client_id`        | token request body                     |
| `client_secret`    | token request body                     |
| `resource`         | token request body (Azure AD resource) |
| `subscription_key` | `Ocp-Apim-Subscription-Key` header     |
| `partner_key`      | request body (`partnerKey`)            |

The SDK fetches, caches and refreshes the bearer token for you (including a one-shot
refresh on a `401`).

### Configuration

Pass values explicitly, or set environment variables and let the client read them:

```
WESTCON_CLIENT_ID, WESTCON_CLIENT_SECRET, WESTCON_RESOURCE,
WESTCON_SUBSCRIPTION_KEY, WESTCON_PARTNER_KEY,
WESTCON_TENANT_ID (optional), WESTCON_GATEWAY_BASE_URL (optional)
```

`WESTCON_TENANT_ID` defaults to Westcon-Comstor's Azure AD tenant (the OAuth
authority in the token-endpoint URL Westcon issues you); set it only to override.
Default gateway: `https://api.westconcomstor.com` (prod), or `uat` per `WESTCON_ENV` below.

**Environments.** Keys are per-environment. Set `WESTCON_ENV=prod` (default) or
`WESTCON_ENV=uat` and the gateway is chosen for you (`prod` →
`https://api.westconcomstor.com`, `uat` → `https://westconapiuat.azure-api.net`). Keys
issued from the **UAT** portal (`westconapiuat.developer.azure-api.net`) only work against
UAT; using them on prod returns `401 invalid subscription key`.

To keep **both** environments in one `.env`, set per-environment variables
(`WESTCON_UAT_*` and `WESTCON_PROD_*`) and flip `WESTCON_ENV` — the environment-specific
value wins over the generic `WESTCON_*`. See [`.env.example`](.env.example). In code,
`Config(..., environment="uat")` does the same.

## Quick start (sync)

```python
from westcon_comstor import WestconComstorClient

with WestconComstorClient(
    client_id="...", client_secret="...", resource="...",
    subscription_key="...", partner_key="...",
) as client:
    # Product availability
    products = client.products.availability(
        country_code="AU",
        products=[{"product_number": "C1111-4P"}],
    )
    for p in products:
        for loc in p.storage_locations:
            print(p.product_number, loc.plant, loc.available_quantity)

    # Pricing
    prices = client.products.pricing(
        country_code="DE", currency="EUR",
        products=[{"product_number": "ASG-WSWS-10-CS"}],
    )

    # Open invoices / orders
    invoices = client.invoices.list(start_date="20250101", end_date="20250201")
    orders = client.orders.open_order_list(start_date="20250101")

    # Order status
    lines = client.orders.status(["600014", "600019"])

    # Quote
    quote = client.quotes.get(quote_id="08XX58X2", reseller_id="0004704", version="0")

    # Shipment tracking
    track = client.shipping.carrier_tracking(
        order_number="201201", carrier="DHL", tracking_number="JD0146...",
    )
    detail = client.shipping.shipment_detail(order_number="59XXXX", tracking_data="Y")

    # Accounts (URUP)
    acct = client.accounts.detail(customer="0011223")
    hits = client.accounts.search(name="Technology Company", country="NL")
```

## Quick start (async)

```python
from westcon_comstor import AsyncWestconComstorClient

async with AsyncWestconComstorClient() as client:   # reads WESTCON_* env vars
    prices = await client.products.pricing(
        country_code="DE", currency="EUR",
        products=[{"product_number": "ASG-WSWS-10-CS"}],
    )
```

## API map

| Namespace          | Method                              | Endpoint                                   |
| ------------------ | ----------------------------------- | ------------------------------------------ |
| `client.invoices`  | `list()`                            | `POST /OpenInvoiceList/GetList`            |
| `client.orders`    | `open_order_list()`                 | `POST /OpenOrders/GetList`                 |
| `client.orders`    | `status()`                          | `POST /Orders/orderStatus`                 |
| `client.orders`    | `status_value()`                    | `POST /orderstatusvalue/getorderstatusvalue` |
| `client.orders`    | `invoiced_lines()`                  | derived (Order Status, `INV` lines)        |
| `client.orders`    | `invoices()`                        | derived (`INV` lines grouped by invoice)   |
| `client.products`  | `availability()`                    | `POST /api/products/availability`          |
| `client.products`  | `pricing()`                         | `POST /Pricing/RetrievePrice`              |
| `client.quotes`    | `get()`                             | `POST /QuoteDetail/retrieve`               |
| `client.shipping`  | `carrier_tracking()`                | `POST /CarrierTracking/GetTrackingInfo`    |
| `client.shipping`  | `shipment_detail()`                 | `POST /shipping/ShipmentDetail`            |
| `client.accounts`  | `detail()`                          | `POST /accountdetail/getaccountdetail`     |
| `client.accounts`  | `search()`                          | `POST /accountsearch/getaccounts`          |
| `client.aem`       | `order_now()`                       | `POST /aem-secure-content/order_now`       |
| `client.fx`        | `implied_rate()`, `rates()`         | derived (Pricing API)                      |
| `client.request()` | generic escape hatch (PartnerView)  | any                                        |

## Derived exchange rates (`client.fx`)

Comstor has no exchange-rate endpoint, but its pricing engine converts a product's base
price into whatever `currency` you request. `client.fx` prices the same product(s) in two
currencies and divides the returned **list prices** to get the effective rate Comstor uses
(margin included). Pass several products to verify the rate is consistent:

```python
rate = client.fx.implied_rate(base="USD", quote="SEK", products="SW-FWSWS-ASG-S500")
print(rate.rate)          # median implied USD->SEK

# multiple base currencies against one target (SEK prices fetched once):
for r in client.fx.rates(bases=["EUR", "USD"], quote="SEK",
                         products=["SKU1", "SKU2", "SKU3"], country="SE"):
    print(r.base_currency, r.rate, "spread", r.spread, "n", r.sample_count)
    for s in r.samples:            # per-product cross-check
        print(" ", s.product_number, s.base_price, "->", s.quote_price, s.rate)
```

`ImpliedRate` carries `rate` (median), `mean`, `minimum`, `maximum`, `spread`,
`sample_count`, per-product `samples`, and `skipped` (products missing a price in one
currency). Uses `listPrice` by default (`price_field="customer"` to switch). It's a
*snapshot* — re-run to track changes. See [`examples/fx_rates.py`](examples/fx_rates.py).

## Errors

All exceptions derive from `westcon_comstor.WestconComstorError`. HTTP failures raise an
`APIStatusError` subclass (`BadRequestError`, `UnauthorizedError`, `ForbiddenError`,
`NotFoundError`, `UnprocessableEntityError`, `RateLimitError`, `ServerError`) carrying
`status_code`, parsed `body`, and the APIM `request_id` (quote it in Westcon support
tickets). Token failures raise `AuthenticationError`; network/timeout failures raise
`APIConnectionError` / `APITimeoutError`.

## Logging

The SDK logs to the `westcon_comstor` logger and is silent until your app adds a handler:

```python
import logging
logging.getLogger("westcon_comstor").setLevel(logging.DEBUG)  # DEBUG: path, timing, request_id
# WARNING level shows retries only.
```

It logs request method + URL, response status/latency, the APIM `request_id`, and retries.
It **never** logs credentials, tokens, headers, or request/response bodies (so no partner
key, no customer PII).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Roadmap

- **Phase 2 — PartnerView** (50+ ops: Commerce Webservices v2 — cart, onboarding,
  finance, master data; REST path/query params). Callable today via `client.request(...)`.
