import os, sys, django
sys.path.insert(0, r"C:\Users\DELL\Documents\projects\freshfarm")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freshapp.settings")
django.setup()

from core_app.models import CollectionCenter
from core_order.models import Order

# Center id=2 belongs to "Deepak" (capital D) — the app login user
app_center = CollectionCenter.objects.get(id=2)
print(f"Reassigning orders to center: {app_center.center_name} (id={app_center.id}, user={app_center.user.username})")

updated = Order.objects.filter(
    flow_type="farmer",
    status__in=["placed", "farmer_assigned", "sent_to_collection"]
).update(collection_center=app_center)

print(f"Updated {updated} orders -> collection_center_id={app_center.id}")

# Verify
pending = Order.objects.filter(
    flow_type="farmer",
    collection_center=app_center,
    status__in=["placed", "farmer_assigned", "sent_to_collection"]
)
print(f"\nVerification: {pending.count()} pending orders for center id={app_center.id}")
for o in pending:
    print(f"  Order #{o.id}: status={o.status}, buyer={o.user.username}")
