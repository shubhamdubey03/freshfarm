from rest_framework import serializers
from core_order.models import Delivery, OrderItem
from core_app.models import Address


# ──────────────────────────────────────────
# ORDER ITEMS
# ──────────────────────────────────────────

class DeliveryOrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="variant.product.name", read_only=True
    )
    unit = serializers.CharField(
        source="variant.unit", read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ["product_name", "unit", "quantity", "price"]


# ──────────────────────────────────────────
# DELIVERY LIST
# ──────────────────────────────────────────

class DeliveryListSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    total_price = serializers.DecimalField(
        source="order.total_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    order_type = serializers.CharField(
        source="order.order_type", read_only=True
    )
    pickup = serializers.SerializerMethodField()
    deliver_to = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id",
            "order_id",
            "status",
            "source_type",
            "pickup",
            "deliver_to",
            "otp",
            "total_price",
            "order_type",
        ]

    def get_pickup(self, obj):
        if obj.source_type == "collection_center" and obj.pickup_center:
            center = obj.pickup_center
            return {
                "type": "collection_center",
                "name": center.center_name,
                "address": center.address,
                "city": center.city,
                "latitude": str(center.latitude) if center.latitude else None,
                "longitude": str(center.longitude) if center.longitude else None,
            }

        elif obj.source_type == "vendor" and obj.vendor:
            vendor = obj.vendor
            address = vendor.user.user_address.first()
            return {
                "type": "vendor",
                "name": vendor.farm_name,
                "address": address.address_line if address else None,
                "city": address.city.name if address else None,
                "latitude": str(address.latitude) if address else None,
                "longitude": str(address.longitude) if address else None,
            }
        return None

    def get_deliver_to(self, obj):
        user = obj.order.user
        address = obj.order.address
        return {
            "customer_name": user.username,
            "phone": user.phone,
            "address_line": address.address_line,
            "city": address.city.name,
            "pincode": address.pincode,
            "latitude": str(address.latitude),
            "longitude": str(address.longitude),
        }


# ──────────────────────────────────────────
# DELIVERY DETAIL
# ──────────────────────────────────────────

class DeliveryDetailSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    total_price = serializers.DecimalField(
        source="order.total_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    order_type = serializers.CharField(
        source="order.order_type", read_only=True
    )
    payment_status = serializers.CharField(
        source="order.payment_status", read_only=True
    )
    pickup = serializers.SerializerMethodField()
    deliver_to = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id",
            "order_id",
            "status",
            "source_type",
            "pickup",
            "deliver_to",
            "items",
            "otp",
            "total_price",
            "order_type",
            "payment_status",
            "pickup_time",
            "delivery_time",
        ]

    def get_pickup(self, obj):
        if obj.source_type == "collection_center" and obj.pickup_center:
            center = obj.pickup_center
            return {
                "type": "collection_center",
                "name": center.center_name,
                "address": center.address,
                "city": center.city,
                "latitude": str(center.latitude) if center.latitude else None,
                "longitude": str(center.longitude) if center.longitude else None,
            }
        elif obj.source_type == "vendor" and obj.vendor:
            vendor = obj.vendor
            address = vendor.user.user_address.first()
            return {
                "type": "vendor",
                "name": vendor.farm_name,
                "address": address.address_line if address else None,
                "city": address.city.name if address else None,
                "latitude": str(address.latitude) if address else None,
                "longitude": str(address.longitude) if address else None,
            }
        return None

    def get_deliver_to(self, obj):
        user = obj.order.user
        address = obj.order.address
        return {
            "customer_name": user.username,
            "phone": user.phone,
            "address_line": address.address_line,
            "city": address.city.name,
            "pincode": address.pincode,
            "latitude": str(address.latitude),
            "longitude": str(address.longitude),
        }

    def get_items(self, obj):
        items = OrderItem.objects.filter(order=obj.order)
        return DeliveryOrderItemSerializer(items, many=True).data


# ──────────────────────────────────────────
# DELIVERY HISTORY
# ──────────────────────────────────────────

class DeliveryHistorySerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id",
            "order_id",
            "status",
            "source_type",
            "pickup_time",
            "delivery_time",
        ]