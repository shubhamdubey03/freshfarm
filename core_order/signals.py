# In your signal or order delivery view

from django.db.models.signals import post_save
from django.dispatch import receiver
from core_order.models import Order
from core_order.utility import auto_assign_delivery


from decimal import Decimal
from core_order.models import AdminCommission,Order

def on_vendor_order_delivered(order: Order):
    if order.flow_type != "vendor":
        return

    rate = Decimal("10.00")
    commission_amount = (order.total_price * rate) / Decimal("100")

    AdminCommission.objects.get_or_create(
        order=order,
        defaults={
            "vendor": order.vendororder.vendor,  # via VendorOrder FK
            "order_total": order.total_price,
            "commission_rate": rate,
            "commission_amount": commission_amount,
        }
    )


from django.db.models.signals import post_save
from django.dispatch import receiver
from core_order.models import Order


# core_order/signals.py
@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):

    if instance.status == "at_collection_center":
        # Farmer flow — delivery boy picks up from collection center
        delivery, success, error = auto_assign_delivery(instance)
        if not success:
            print(f"[AUTO ASSIGN FAILED] Order #{instance.id} — {error}")

    # elif instance.status == "placed" and instance.flow_type == "vendor":
    #     # Vendor flow — auto assign vendor (separate service)
    #     from core_order.utility import auto_assign_vendor
    #     auto_assign_vendor(instance)         