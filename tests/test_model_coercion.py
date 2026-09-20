"""WestconModel coerces null array fields to [] (Comstor sends null for empty arrays)."""

from westcon_comstor.models.shipping import ShipmentTrackingResult
from westcon_comstor.models.orders import OrderStatusValueResult


def test_none_list_fields_coerced_to_empty():
    # CarrierTracking: Comstor returns serviceEvents/additionalImages as null when empty.
    r = ShipmentTrackingResult.model_validate({
        "orderNumber": "0004608324", "carrier": "Fedex Regional Economy",
        "trackingNumber": "876187534286", "serviceEvents": None, "additionalImages": None,
    })
    assert r.service_events == [] and r.additional_images == []
    assert r.tracking_number == "876187534286"


def test_populated_list_still_parses():
    r = ShipmentTrackingResult.model_validate(
        {"serviceEvents": [{"eventDescription": "Picked up", "eventLocation": "ARN"}]})
    assert len(r.service_events) == 1
    assert r.service_events[0].event_description == "Picked up"


def test_none_lists_on_another_model():
    r = OrderStatusValueResult.model_validate({"orderStatus": None, "orderValue": None})
    assert r.order_status == [] and r.order_value == []
