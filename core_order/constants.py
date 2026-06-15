from django.db import models

class OrderStatus(models.TextChoices):
    PLACED = "placed", "Placed"
    FARMER_ASSIGNED = "farmer_assigned", "Farmer Assigned"
    SENT_TO_COLLECTION = "sent_to_collection", "Sent To Collection"
    AT_COLLECTION_CENTER = "at_collection_center", "At Collection Center"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out For Delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    RETURNED = "returned", "Returned"


class DeliveryStatus(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    PICKED = "picked", "Picked"
    PICKED_UP = "picked_up", "Picked Up"
    DELIVERED = "delivered", "Delivered"
    RETURNED = "returned", "Returned"