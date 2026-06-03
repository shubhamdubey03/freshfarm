import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freshfarm.settings")
django.setup()

from core_order.models import Order, VendorOrder, SellerEarning, Delivery

try:
    order = Order.objects.get(id=11)
    print("--- Order #11 ---")
    print(f"Status: {order.status}")
    print(f"Total Price: {order.total_price}")
    print(f"Flow Type: {order.flow_type}")
    
    try:
        vo = order.vendororder
        print("\n--- VendorOrder ---")
        print(f"Status: {vo.status}")
        print(f"Vendor: {vo.vendor}")
    except Exception as e:
        print(f"\nNo VendorOrder linked: {e}")
        
    earnings = SellerEarning.objects.filter(order=order)
    print(f"\n--- Seller Earnings ({earnings.count()}) ---")
    for e in earnings:
        print(f"ID: {e.id}, Seller: {e.seller}, Amount: {e.amount}, Settled: {e.is_settled}")
        
    try:
        deliv = order.delivery
        print("\n--- Delivery ---")
        print(f"Status: {deliv.status}")
        print(f"Delivery Boy: {deliv.delivery_boy}")
    except Exception as e:
        print(f"\nNo Delivery: {e}")

except Order.DoesNotExist:
    print("Order #11 not found.")
