# Westcon-Comstor AIM — API reference (as captured from the developer portal)

Source: <https://api-portal.westconcomstor.com/> (Azure API Management developer portal).
Gateway base URL: `https://api.westconcomstor.com`. Captured 2026-09-13.

This documents the **12 core transactional APIs** implemented in Phase 1. PartnerView is
covered in [PARTNERVIEW_NOTES.md](PARTNERVIEW_NOTES.md).

## Authentication — OAuth 2.0 client credentials (Azure AD v1)

`POST https://login.microsoftonline.com/ec8933c6-cfb2-4dd9-bfc9-621cde1dea8f/oauth2/token`
(Westcon-Comstor's Azure AD tenant — the OAuth authority; the SDK defaults to it.)
Content-Type `application/x-www-form-urlencoded`, body:

| field         | value               |
| ------------- | ------------------- |
| client_id     | (issued by Westcon) |
| client_secret | (issued by Westcon) |
| grant_type    | `client_credentials`|
| resource      | (issued by Westcon) |

Response: `{ token_type: "Bearer", expires_in, expires_on, access_token, ... }`.
Send `Authorization: Bearer <access_token>` + `Ocp-Apim-Subscription-Key: <key>` on every
gateway call. Most request bodies also carry a `partnerKey` (reseller identifier).

All 12 core operations are **POST** with `application/json` bodies. Field casing is exactly
as Westcon documents it (note the irregular `eRPOrderNumber`, PascalCase blocks, and the
`mT_*`/`MT_*` envelope keys); the SDK models normalise these.

---

## Orders & Invoices

### Open Invoice List — `POST /OpenInvoiceList/GetList`
Request `MT_InvoiceList_S_Req`: `partnerKey`*, `startDate`* (YYYYMMDD), `endDate`.
Response `MT_InvoiceList_S_Resp.invoice[]`: billingDocument, customerOrderNumber,
eRPOrderNumber, payer, billingDate, totalValue, currency, status, paymentTerms, dueDate;
plus `error{error, errorDescription}`.

### Open Order List — `POST /OpenOrders/GetList`
Request `MT_OpenOrderList_Req`: `partnerKey`*, `startDate`*, `endDate`.
Response `MT_OpenOrderList_S_Resp.openOrderList[]`: salesOrderNumber, orderDate,
customerPONumber, amount, currency, endUserName, westconSalesOrg, country; plus `error`.

### Order Status — `POST /Orders/orderStatus`
Request `MT_OrderStatus_API_REQ`: `partnerKey`*, `orderType`* (W/C), `language`*,
`order[]`* (order-number strings, or objects with orderNumber + secondary VRF fields),
`secondaryVRFReferenceField`, `secondaryVRFReferenceValue`.
Response `MT_OrderStatus_Response[]`: eRPOrderNumber, eRPOrderLineNumber, customerOrderNumber,
CustomerLongPONumber, customerLineNumber, eRPProductNumber, lineQuantity, unitOfMeasure,
lineStatusCode, lineStatusDescription, statusDate, (E)stimatedShipDate, estimatedDeliveryDate,
shipDate, billingDocument, parentERPLine, vendorSalesOrderNumber.

### Order Status Value — `POST /orderstatusvalue/getorderstatusvalue`  (URUP)
Request `MT_OrderStatusValue_API_REQ`: partnerKey, order_type, language, order[] (strings).
Response `MT_OrderStatusValue_Response`: `orderStatus[]` (eRPOrderNumber, eRPOrderLineNumber,
customerOrderNumber, customerLineNumber, eRPProductNumber, lineQuantity, unitOfMeasure,
lineStatusCode, lineStatusDescription, statusDate, shipDate, billingDocument, parentERPLine)
and `orderValue[]` (eRPOrderNumber, customerOrderNumber, value, currency).

## Product Information

### Availability — `POST /api/products/availability`
Request `Availability_Request`: partnerKey, countryCode, products[]{productNumber, longProductNumber}.
Response `Availability_Response[]`: ProductNumber, LongProductNumber,
storage_locations[]{Plant, LocationNumber, AvailableQuantity(number), LeadTimeInDays(number),
POQuantity(number), PODate(date)}, error{errorNumber, errorDescription}.

### Pricing — `POST /Pricing/RetrievePrice`
Request `MT_Pricing_S_Req.pricing`: partnerKey*, countryCode*, customerPrice* (Y/N), currency*,
products[]{productNumber*, longProductNumber}.
Response `MT_Pricing_Resp[]`: product{productNumber, longProductNumber, listPrice(number),
customerPrice(number), currency}, error{errorNumber, errorDescription}.

## Quoting

### Get Quote — `POST /QuoteDetail/retrieve`
Request (flat): `partnerKey`*, `resellerId`*, `quoteId`*, `version`* (empty = latest).
Response `GetQuoteResponse`: message, success, quoteData{...large...}. On error, HTTP 500 with
`{success:false, message}`. Shared types: Price{currencyIso, formattedValue, value, valueWithoutCurrency},
Account, Address, Comments, periodicBilling. quoteData has ~100 fields incl. entries[]
(product, prices, VRF lines, periodic billing), totals, accounts, addresses, quoteInformation.

## Shipping & Delivery

### Carrier Tracking — `POST /CarrierTracking/GetTrackingInfo`
Request `shipmentTracking.mT_ShipmentTracking_API_Req`: partnerKey*, orderNumber*, carrier*, trackingNumber*.
Response `shipmentTrackingResponse.shipmentTrackingResult`: orderNumber, carrier, trackingNumber,
shipmentDate, pieces, weight, weightUnit, estimatedDeliveryDate, deliveryDate, signature,
signatureImage(base64), signatureImageType, additionalImages[]{image, imageDate, imageType},
serviceEvents[]{eventDate, eventTime, eventLocation, eventDescription}, errorCode, errorDescription.

### Shipment Detail — `POST /shipping/ShipmentDetail`
Request `mT_OrderTrack_API_Req`: partnerKey*, orderType* (W/C), language*, orderNumber*,
trackingData (Y/N), serialData (Y/N), vrfData (Y/N), secondaryVRFReferenceField/Value.
(Note: portal table misspells `order_type`/`orderNUmber`; the working example uses
`orderType`/`orderNumber`, which the SDK sends.)
Response `mT_OrderTrack_Response`: OrderStatus[], OrderTracking[]{..., TrackingNo, Carrier},
OrderSerialNum[]{..., ManufSerialNo, MACAddress, TrackingNo}, OrderVRFData[]{..., Name, Value}.

## URUP Accounts

### Account Detail — `POST /accountdetail/getaccountdetail`
Request `mT_AccountDetail_S_Req`: customer, partnerKey.
Response `mT_AccountDetail_S_Resp`: customerDetails{name, name2-4, street, street2-5, city,
district, postalCode, region, countryKey}, contactDetails[]{fullName, firstName, lastName, eMail, phone}.

### Account Search — `POST /accountsearch/getaccounts`
Request `mT_AccountSearch_S_Req`: name, customer, country, partnerKey.
Response `mT_AccountSearch_S_Resp`: totalCount, customerDetails[]{customer, country, name1,
city, postalCode, region}. (Example returns `TotalCount`/`CustomerDetails` PascalCase — SDK accepts both.)

## Untagged

### AEM Secure Content — `POST /aem-secure-content/order_now`
Request (free-form, ServiceNow-style): `sysparm_quantity`, `variables{user_name, group_name,
request_origin, request_origin_title, request_title, request_destination}`. Response: none documented.

(*) required field.
