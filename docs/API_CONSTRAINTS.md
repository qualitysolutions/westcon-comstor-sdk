# API constraints & gotchas (from live UAT testing)

Behaviours confirmed live on 2026-09-13 that aren't obvious from the docs. Invoice-specific
findings live in [INVOICE_RETRIEVAL.md](INVOICE_RETRIEVAL.md); this file covers pricing,
orders, errors and access scope.

## Pricing is country-scoped, currency is not

- `country_code` is locked to the **partner's own market**. For the Swedish partner,
  `SE` works; `DE`, `NO`, `GB` all return the per-request error **"Not Valid Input"**.
  Other markets need their own partner account.
- **Currency can vary within the allowed country.** `country="SE"` prices fine in `SEK`,
  `EUR` and `USD`. This is why the FX tool (`client.fx`) holds the country fixed and only
  varies the currency.

## listPrice vs customerPrice

- `list_price` is the catalogue list price; `customer_price` is the reseller's
  **discounted** price (observed ~38% below list, e.g. list 1 000.00 vs
  customer 620.00 SEK — illustrative figures).
- `pricing()` defaults to `customer_price="Y"`, so both come back. **The FX derivation
  must use `list_price`** — customer discounts vary per line/account and would pollute the
  rate. `client.fx` uses `price_field="list"` by default for exactly this reason.

## Availability: stock vs lead time are independent

`availability()` returns one or more `storage_locations` per product, each with
`plant`/`location_number`, `available_quantity` (units in stock), `lead_time_in_days`
(delivery lead time), and `po_quantity`/`po_date` (inbound purchase-order stock + restock
date).

**`lead_time_in_days` is populated even when `available_quantity` is 0.** In UAT no stock
is seeded (`available_quantity == 0` everywhere), yet the lead times are real and
per-product — e.g. one product came back at 80 days while others were 3 days. So a 0
quantity does **not** mean "no data": always read `lead_time_in_days` and
`po_date` for delivery estimates. In production, `available_quantity` reflects real on-hand
stock and `po_date` the expected restock date.

## Errors are per-product, not exceptions

- An invalid product number does **not** raise. Pricing returns a row with
  `error = {error_number: "A01", error_description: "Invalid Material"}`; availability
  returns `error_number "A01"` / "Plant could not be determined...". Check the `error`
  field per product; a populated `error` means that line failed while others may succeed.
- HTTP-level failures (auth, 5xx, 404) still raise `APIStatusError` subclasses.

## Order lookup and enumeration

- **`order_type`**: `"W"` = Westcon sales order number, `"C"` = customer PO number.
- **A customer PO can map to multiple Westcon orders**, and `order_type="C"` can surface
  orders **beyond** the open-order list (e.g. PO `PO-0001` → orders `0000000001` *and*
  `0000000005`). If you know a customer PO, this is a way to discover related/closed
  orders that Open Order List won't return.
- **Open Order List returns only orders with open lines** — it is not a full order history.
  There is no "all orders" endpoint in the core set (that's BlueSky "List Orders").
- **`NAO` ("Not Authentic Order")**: Order Status returns a single line with
  `line_status_code == "NAO"` for a well-formed order number that isn't owned by the
  current `partner_key` (different reseller, or a production order queried against UAT).
  It's an ownership/environment signal, not a format problem. Pass `partner_key=` per call
  to query under another reseller.

## Access scope (this UAT subscription)

- **Works**: Pricing, Availability, Order Status, Open Order List, Shipment Detail,
  Get Quote (reachable), plus the derived `fx`, `serials`, `invoiced_lines`, `invoices`.
- **URUP Account APIs** (Account Detail, Account Search, Order Status Value): return
  **401 invalid subscription key** — not included in this subscription's product.
- **BlueSky**: returns **404** on the UAT gateway (not exposed there, or a different path);
  it also uses a separate header auth. Parked — see [PARTNERVIEW_NOTES.md](PARTNERVIEW_NOTES.md)
  and request access + spec from Westcon.

## Environment / data notes

- UAT and production are **separate datasets**. UAT order numbers seen: `0060xxxxxx`
  (older), `0004xxxxxx` / `0040xxxxxx`. Production order/invoice/delivery numbers do not
  resolve against the UAT gateway.
- Availability quantities are often **0** in UAT (no stock seeded); the numeric fields
  (`available_quantity`, `lead_time_in_days`, `po_quantity`) parse correctly regardless.
