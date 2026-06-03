import os, sys, django
sys.path.insert(0, r"C:\Users\DELL\Documents\projects\freshfarm")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freshapp.settings")
django.setup()

import requests
from core_app.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# Use the CAPITAL-D Deepak (id=10) — the app login user
user = User.objects.get(id=10)
print(f"Testing as: {user.username} (id={user.id}, role={user.role})")

token = str(RefreshToken.for_user(user).access_token)
headers = {"Authorization": f"Bearer {token}"}

r = requests.get("http://127.0.0.1:8000/collection/orders/pending/", headers=headers, timeout=5)
print(f"\nGET /collection/orders/pending/")
print(f"  Status: {r.status_code}")
data = r.json()
print(f"  Count: {data.get('count', 0)}")
for order in data.get('results', []):
    print(f"  Order #{order['id']}: status={order['status']}, farmer={order.get('farmer')}, items={order.get('items')}")
