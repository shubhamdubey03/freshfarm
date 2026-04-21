from django.db import models

class OrderStatus(models.TextChoices):
    PLACED = "placed", "Placed"
    FARMER_ASSIGNED = "farmer_assigned", "Farmer Assigned"
    SENT_TO_COLLECTION = "sent_to_collection", "Sent To Collection"
    AT_COLLECTION_CENTER = "at_collection_center", "At Collection Center"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out For Delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class DeliveryStatus(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    PICKED = "picked", "Picked"
    DELIVERED = "delivered", "Delivered"