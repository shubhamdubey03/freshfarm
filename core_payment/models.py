from django.db import models
from core_order.models import *

# Create your models here.
class Payment(models.Model):

    PAYMENT_METHOD = (
        ("upi", "UPI"),
        ("card", "Card"),
        ("cod", "Cash On Delivery"),
    )

    order = models.ForeignKey("core_order.Order", on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    method = models.CharField(max_length=20, choices=PAYMENT_METHOD)

    transaction_id = models.CharField(max_length=200)

    status = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)                