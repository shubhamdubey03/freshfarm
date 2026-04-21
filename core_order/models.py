from django.db import models
from core_app.models import *
from core_product.models import *
from core_order.constants import OrderStatus, DeliveryStatus

# Create your models here.
class Order(models.Model):

    STATUS_CHOICES = (
        ("placed", "Placed"),
        ("farmer_assigned", "Farmer Assigned"),
        ("sent_to_collection", "Sent To Collection Center"),
        ("at_collection_center", "At Collection Center"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    ORDER_TYPE_CHOICES = (
        ("pre_order", "Pre Order"),
        ("subscription", "Subscription"),
        ("cod", "Cash on Delivery"),
        ("paid", "Online Paid"),
    )

    PAYMENT_STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    FLOW_TYPE = (
        ("vendor", "Vendor Delivery"),
        ("farmer", "Farmer via Collection Center"),
    )

    flow_type = models.CharField(max_length=20, choices=FLOW_TYPE,default="farmer")

    user = models.ForeignKey("core_app.User", on_delete=models.CASCADE)
    address = models.ForeignKey("core_app.Address", on_delete=models.CASCADE)

    collection_center = models.ForeignKey(
        "core_app.CollectionCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # 🔥 NEW
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default="pre_order")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="pending")

    delivery_date = models.DateField(null=True, blank=True)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    variant = models.ForeignKey(
        "core_product.ProductVariant",
        on_delete=models.CASCADE
    )

    # 🔥 NEW (IMPORTANT)
    seller = models.ForeignKey(
        "core_app.Seller",
        on_delete=models.CASCADE,
        null=True,      # 👈 IMPORTANT
        blank=True
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.IntegerField()

class OrderStatusHistory(models.Model):
    STATUS_CHOICES = (
        ("placed", "Placed"),
        ("at_collection_center", "At Collection Center"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="status_history")

    status = models.CharField(max_length=50,choices=STATUS_CHOICES)

    updated_by = models.ForeignKey(
        "core_app.User",
        on_delete=models.SET_NULL,
        null=True
    )

    updated_at = models.DateTimeField(auto_now_add=True)


class Delivery(models.Model):

    DELIVERY_SOURCE = (
        ("vendor", "Vendor"),
        ("collection_center", "Collection Center"),
    )

    order = models.OneToOneField("core_order.Order", on_delete=models.CASCADE)

    source_type = models.CharField(max_length=20, choices=DELIVERY_SOURCE, default="collection_center")

    vendor = models.ForeignKey(
        "core_app.Seller",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    pickup_center = models.ForeignKey(
        "core_app.CollectionCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    delivery_boy = models.ForeignKey("core_app.User", on_delete=models.SET_NULL, null=True)

    status = models.CharField(max_length=50, choices=DeliveryStatus.choices,
    default=DeliveryStatus.ASSIGNED)

    otp = models.CharField(max_length=6)

    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)


class SellerEarning(models.Model):

    seller = models.ForeignKey("core_app.Seller", on_delete=models.CASCADE)

    order = models.ForeignKey("core_order.Order", on_delete=models.CASCADE)

    order_item = models.ForeignKey("core_order.OrderItem", on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    is_settled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

class SellerPayout(models.Model):

    seller = models.ForeignKey("core_app.Seller", on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    start_date = models.DateField()
    end_date = models.DateField()

    is_paid = models.BooleanField(default=False)

    paid_at = models.DateTimeField(null=True, blank=True)

class FarmerOrderBatch(models.Model):

    date = models.DateField()  

    cutoff_time = models.DateTimeField()  

    is_closed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)


class FarmerOrder(models.Model):

    order_item = models.ForeignKey("core_order.OrderItem", on_delete=models.CASCADE)

    farmer = models.ForeignKey("core_app.Seller", on_delete=models.CASCADE)

    batch = models.ForeignKey(FarmerOrderBatch, on_delete=models.CASCADE)

    quantity = models.IntegerField()

# Add to core_order/models.py or a new core_finance/models.py

class FarmerSalary(models.Model):
    farmer = models.ForeignKey(
        "core_app.Seller",
        on_delete=models.CASCADE,
        related_name="salaries",
        limit_choices_to={"seller_type": "farmer"}
    )
    month = models.DateField()  # store as first day: 2025-01-01 = Jan 2025
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)  # optional admin remark

    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("farmer", "month")  # one salary per farmer per month

    def __str__(self):
        return f"{self.farmer} - {self.month.strftime('%b %Y')}"


class AdminCommission(models.Model):
    order = models.OneToOneField(
        "core_order.Order",
        on_delete=models.CASCADE,
        related_name="commission"
    )
    vendor = models.ForeignKey(
        "core_app.Seller",
        on_delete=models.CASCADE,
        limit_choices_to={"seller_type": "vendor"}
    )
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00  # percentage
    )
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)

    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission ₹{self.commission_amount} on Order #{self.order_id}"

