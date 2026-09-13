# Invoice retrieval — findings (UAT, 2026-09-13)

How to get invoice data out of the Westcon-Comstor AIM APIs, based on live UAT testing.
Short version: you can retrieve invoice **numbers and their line items**, but **not PDF
invoice documents**, and the "Open Invoice List" endpoint only surfaces *outstanding*
invoices.

## 1. Open Invoice List returns only OUTSTANDING invoices

`client.invoices.list(start_date=..., end_date=...)` (`POST /OpenInvoiceList/GetList`) is
the *open/unpaid* invoice view. For the UAT test partner it returns **0 invoices** across
every date range tried (2018-2026), with the backend business message:

```
error = { error: "N", errorDescription: "No Open Order Selected For Given Input" }
```

So an empty result here means "no outstanding invoices", not "no invoices exist".

## 2. Invoice numbers come from the invoiced order lines

Invoices (SAP billing documents) are attached to each **invoiced** order line and are
retrievable via Order Status / Shipment Detail:

- `client.orders.status([order_no])` → `OrderStatusLine.billing_document`
- `client.shipping.shipment_detail(order_number=order_no)` → `order_status[].billing_document`

Filter lines by `line_status_code == "INV"` (Invoiced). Each line also carries
`erp_product_number`, `line_quantity`, `unit_of_measure`, `status_date`, `ship_date` and
`vendor_sales_order_number`. Group lines by `billing_document` to reconstruct each invoice.

Invoice numbers in this environment look like `10350xxxxx` (10 digits, `10350` prefix).

## 2b. What fields are available

Two different shapes, depending on the source:

**Invoice header** — from Open Invoice List (`Invoice` model). These are the "real"
invoice fields incl. money, but this endpoint is **empty for the UAT test partner**, so we
never actually receive values for them here:

- `billing_document` (invoice number), `erp_order_number`, `customer_order_number`
- `payer`, `billing_date`, `due_date`, `payment_terms`, `status`
- `total_value`, `currency`

**Invoiced line** — from Order Status / Shipment Detail (`OrderStatusLine` /
`OrderStatusDetail`, filtered to `INV`). This is what we can actually retrieve now:

- `billing_document` (invoice number), `erp_order_number`, `erp_order_line_number`, `parent_erp_line`
- `customer_order_number`, `customer_long_po_number`, `customer_line_number`
- `erp_product_number`, `line_quantity`, `unit_of_measure`
- `line_status_code` / `line_status_description` (e.g. `INV` = Invoiced)
- `status_date`, `ship_date`, `estimated_ship_date`, `estimated_delivery_date`
- `vendor_sales_order_number`

Important gaps:
- The invoiced-line route has **no monetary amounts** (no unit/line price, no tax, no line
  total). Amounts (`total_value`, `currency`) live only on the invoice header from Open
  Invoice List — which returns nothing for this partner. So in this environment we can list
  invoice numbers and their line items, but **not invoice totals/amounts**.
- **No serial numbers.** Neither the invoice header nor the invoiced line carries a serial.
  Serials come only from Shipment Detail's `OrderSerialNum` block (`serial_data="Y"`), which
  is empty for these orders (drop-ship / non-tangible). So there are no serials in the
  invoice data.

## 3. Worked example — order `0000000004`

21 lines total, 14 invoiced across **3 invoices**:

| Invoice (billing doc) | Date | Lines | Contents |
| --- | --- | --- | --- |
| `9000000003` | 2026-03-02 | 000010-000100 (10) | Meraki licences (LIC-MG21/MG51/ENT/MS120/MS130/MX67/MT/Z4C) |
| `9000000004` | 2026-03-05 | 000110, 000130 | Hardware: MR44-HW ×4, MX67-HW ×2 |
| `9000000005` | 2026-03-05 | 000120, 000140 | LIC-ENT-1YR ×4, LIC-MX67-ENT-1YR ×2 |

(One order can span several invoices; licence and hardware lines are billed separately.)

## 4. No PDF / document download

There is **no invoice-PDF or document endpoint** in the accessible API set:

- Open Invoice List returns metadata only (billing document number, dates, total value,
  currency, status, due date).
- Order/Shipment Detail returns the billing document **number**, not the document.
- Carrier Tracking *does* return base64 documents, but those are proof-of-delivery /
  signature images, not invoices.
- Document/attachment/report **downloads exist only in BlueSky** ("Download attachment",
  "Download Report") — the out-of-scope API, not in this subscription.
- The Technical Guide references an "Invoice Detail" API, but it is not present in the
  subscribed API list.

To obtain actual PDF invoices you would need BlueSky's download operations (a separate
subscription/scope) or the Westcon partner portal.

## 5. Scope note — "Not Authentic Order"

Order Status returns a single line with `lineStatusCode == "NAO"` ("Not Authentic Order")
for an order number that is well-formed but not owned by the current `partnerKey`. This is
an ownership/environment signal, not a format error — an order from another reseller or
from production reads as NAO against a given UAT partner key. Pass `partner_key=` per call
to query under a different reseller.
