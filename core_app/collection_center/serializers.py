from rest_framework import serializers
from core_app.models import CollectionCenter, CollectionOrder
from core_order.models import Delivery, OrderItem


# ──────────────────────────────────────────
# PROFILE
# ──────────────────────────────────────────

class CollectionCenterProfileSerializer(serializers.ModelSerializer):

    phone = serializers.CharField(source="user.phone", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = CollectionCenter
        fields = [
            "id",
            "center_name",
            "address",
            "city",
            "state",
            "latitude",
            "longitude",
            "is_verified",
            "phone",
            "username",
        ]
        read_only_fields = ["is_verified"]


class CollectionCenterProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CollectionCenter
        fields = ["address", "city", "state", "latitude", "longitude"]


# ──────────────────────────────────────────
# ORDER ITEMS
# ──────────────────────────────────────────

class CollectionOrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="variant.product.name", read_only=True
    )
    unit = serializers.CharField(
        source="variant.unit", read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ["id", "product_name", "unit", "quantity", "price"]


# ──────────────────────────────────────────
# COLLECTION ORDER LIST
# ──────────────────────────────────────────

class CollectionOrderListSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    farmer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CollectionOrder
        fields = [
            "id",
            "order_id",
            "status",
            "farmer",
            "items",
            "created_at",
        ]

    def get_farmer(self, obj):
        # get farmer from order items
        order_item = OrderItem.objects.filter(
            order=obj.order
        ).select_related("seller__user").first()

        if not order_item or not order_item.seller:
            return None

        return {
            "farm_name": order_item.seller.farm_name,
            "phone": order_item.seller.user.phone,
        }

    def get_items(self, obj):
        items = OrderItem.objects.filter(order=obj.order)
        return CollectionOrderItemSerializer(items, many=True).data


# ──────────────────────────────────────────
# COLLECTION ORDER DETAIL
# ──────────────────────────────────────────

class CollectionOrderDetailSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    farmer = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = CollectionOrder
        fields = [
            "id",
            "order_id",
            "status",
            "farmer",
            "customer",
            "items",
        ]

    def get_farmer(self, obj):
        order_item = OrderItem.objects.filter(
            order=obj.order
        ).select_related("seller__user").first()

        if not order_item or not order_item.seller:
            return None

        return {
            "farm_name": order_item.seller.farm_name,
            "phone": order_item.seller.user.phone,
        }

    def get_customer(self, obj):
        user = obj.order.user
        address = obj.order.address
        return {
            "name": user.username,
            "phone": user.phone,
            "address": f"{address.address_line}, {address.city.name}",
        }

    def get_items(self, obj):
        items = OrderItem.objects.filter(order=obj.order)
        return CollectionOrderItemSerializer(items, many=True).data


# ──────────────────────────────────────────
# DELIVERY LIST (from this center)
# ──────────────────────────────────────────

class CollectionDeliveryListSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    delivery_boy = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id",
            "order_id",
            "status",
            "delivery_boy",
            "otp",
            "pickup_time",
        ]

    def get_delivery_boy(self, obj):
        if not obj.delivery_boy:
            return None
        return {
            "name": obj.delivery_boy.username,
            "phone": obj.delivery_boy.phone,
        }