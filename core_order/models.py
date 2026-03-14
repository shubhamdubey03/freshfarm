from django.db import models
from core_app.models import *
from core_product.models import *

# Create your models here.
class Order(models.Model):

    STATUS_CHOICES = (
        ("placed", "Placed"),
        ("admin_approved", "Admin Approved"),
        ("farmer_accepted", "Farmer Accepted"),
        ("sent_to_collection", "Sent To Collection Center"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey("core_app.User", on_delete=models.CASCADE)
    address = models.ForeignKey("core_app.Address", on_delete=models.CASCADE)

    collection_center = models.ForeignKey(
        "core_product.CollectionCenter",
        on_delete=models.SET_NULL,
        null=True
    )

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    variant = models.ForeignKey(
        "core_product.ProductVariant",
        on_delete=models.CASCADE
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.IntegerField()

class OrderStatusHistory(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    status = models.CharField(max_length=50)

    updated_by = models.ForeignKey(
        "core_app.User",
        on_delete=models.SET_NULL,
        null=True
    )

    updated_at = models.DateTimeField(auto_now_add=True)


class Delivery(models.Model):

    order = models.OneToOneField(
        "core_order.Order",
        on_delete=models.CASCADE
    )

    delivery_boy = models.ForeignKey(
        "core_app.User",
        on_delete=models.SET_NULL,
        null=True
    )

    pickup_center = models.ForeignKey(
        "core_product.CollectionCenter",
        on_delete=models.SET_NULL,
        null=True
    )

    status = models.CharField(max_length=50)

    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)

    otp = models.CharField(max_length=6)