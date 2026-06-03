from celery import shared_task
from django.core.cache import cache
from core_app.utils.fcm import send_notification
import json


@shared_task
def assign_next_vendor(order_id):
    """If the vendor does not accept within 30 seconds,
    send the order to the next nearest vendor."""

    from core_app.models import Seller, VendorOrder
    from core_order.models import Order

    queue_key = f"vendor_queue_{order_id}"
    queue_data = cache.get(queue_key)

    if not queue_data:
        print(f"No Vendor queue for Order {order_id}")
        return

    vendor_queue = json.loads(queue_data)

    if not vendor_queue:
        print(f"No more vendor for order {order_id}")

        try:
            order = Order.objects.get(id=order_id)
            send_notification(
                user=order.user,
                title=" No Vendor Available",
                body="No vendors are currently available. Please try again later.",
                data={"type": "no_vendor", "order_id": order_id},
            )
        except:
            pass
        return

    next_vendor_id = vendor_queue.pop(0)

    cache.set(queue_key, json.dumps(vendor_queue), timeout=600)

    try:
        order = Order.objects.get(id=order_id)
        vendor = Seller.object.get(id=next_vendor_id)

        vendor_order = VendorOrder.objects.filter(order=order).first()

        if vendor_order and vendor_order.status != "assigned":

            print(f"Order {order_id} already accepted")
            return

        if vendor_order:
            vendor_order.vendor = vendor
            vendor_order.save()
        else:
            VendorOrder.objects.create(order=order, vendor=vendor, status="assigned")

        send_notification(
            user=vendor.user,
            title="🛒 new order",
            body=f"Order #{order.id} has arrived. Please accept it within 30 seconds!",
            data={"type": "new_order", "order_id": str(order.id), "expires_in": "30"},
        )

        assign_next_vendor.apply_async(args=[order_id], countdown=30)

    except Exception as e:
        print(f"Error assigning vendor : {e}")
