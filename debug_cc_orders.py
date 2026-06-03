import os, sys, django
sys.path.insert(0, r"C:\Users\DELL\Documents\projects\freshfarm")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freshapp.settings")
django.setup()

from core_app.models import User, CollectionCenter
from core_order.models import Order

# Find collection_center users
cc_users = User.objects.filter(role="collection_center")
print("=== Collection Center Users ===")
for u in cc_users:
    try:
        cc = CollectionCenter.objects.get(user=u)
        print(f"  User: {u.username} (id={u.id}) -> Center: {cc.center_name} (id={cc.id})")
    except CollectionCenter.DoesNotExist:
        print(f"  User: {u.username} (id={u.id}) -> NO CollectionCenter record!")

print()
print("=== Orders with flow_type=farmer ===")
orders = Order.objects.filter(flow_type="farmer").select_related("collection_center", "user")
for o in orders:
    cc_name = o.collection_center.center_name if o.collection_center else "NONE"
    cc_id = o.collection_center.id if o.collection_center else "NONE"
    print(f"  Order #{o.id}: status={o.status}, buyer={o.user.username}, cc={cc_name}(id={cc_id})")

print()
print("=== Pending (placed/farmer_assigned/sent_to_collection) ===")
pending = Order.objects.filter(
    flow_type="farmer",
    status__in=["placed", "farmer_assigned", "sent_to_collection"]
)
print(f"  Total: {pending.count()}")
for o in pending:
    cc_name = o.collection_center.center_name if o.collection_center else "NONE"
    cc_id = o.collection_center.id if o.collection_center else "NONE"
    print(f"  Order #{o.id}: status={o.status}, cc={cc_name}(id={cc_id})")
