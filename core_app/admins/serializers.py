# core_app/admin_serializers.py

from rest_framework import serializers
from core_app.models import User, Seller, CollectionCenter
from core_order.models import Order, OrderItem


# ══════════════════════════════════════════════════════════
# FARMER SERIALIZERS
# ══════════════════════════════════════════════════════════

class SellerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = [
            "id",
            "farm_name",
            "farm_location",
            "bank_account",
            "ifsc_code",
            "seller_type",
            "is_verified",
            "created_at",
        ]


class FarmerListSerializer(serializers.ModelSerializer):
    seller = SellerInfoSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "country_code",
            "profile_image",
            "is_verified",
            "created_at",
            "seller",
        ]


class FarmerApproveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])


# ══════════════════════════════════════════════════════════
# VENDOR SERIALIZERS
# ══════════════════════════════════════════════════════════

class VendorListSerializer(serializers.ModelSerializer):
    seller = SellerInfoSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "country_code",
            "profile_image",
            "is_verified",
            "created_at",
            "seller",
        ]


# ══════════════════════════════════════════════════════════
# COLLECTION CENTER SERIALIZERS
# ══════════════════════════════════════════════════════════

class CollectionCenterSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CollectionCenter
        fields = [
            "id",
            "user",
            "center_name",
            "address",
            "city",
            "state",
            "latitude",
            "longitude",
            "is_verified",
            "created_at",
        ]


class CollectionCenterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionCenter
        fields = [
            "center_name",
            "address",
            "city",
            "state",
            "latitude",
            "longitude",
        ]


# ══════════════════════════════════════════════════════════
# ORDER SERIALIZERS
# ══════════════════════════════════════════════════════════

class AdminOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True
    )
    variant_unit = serializers.CharField(
        source="variant.unit",
        read_only=True
    )
    seller_name = serializers.CharField(
        source="seller.farm_name",
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name",
            "variant_unit",
            "seller_name",
            "price",
            "quantity",
        ]


class AdminOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="user.username",
        read_only=True
    )
    customer_phone = serializers.CharField(
        source="user.phone",
        read_only=True
    )
    collection_center_name = serializers.CharField(
        source="collection_center.center_name",
        read_only=True
    )
    items = AdminOrderItemSerializer(
        source="orderitem_set",
        many=True,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_name",
            "customer_phone",
            "flow_type",
            "order_type",
            "status",
            "payment_status",
            "total_price",
            "delivery_date",
            "collection_center_name",
            "items",
            "created_at",
        ]


# ══════════════════════════════════════════════════════════
# DASHBOARD SERIALIZER
# ══════════════════════════════════════════════════════════

class DashboardUserStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    farmers_pending = serializers.IntegerField()
    farmers_approved = serializers.IntegerField()
    vendors_pending = serializers.IntegerField()
    vendors_approved = serializers.IntegerField()
    delivery_boys = serializers.IntegerField()


class DashboardOrderStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    placed = serializers.IntegerField()
    delivered = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class DashboardSerializer(serializers.Serializer):
    users = DashboardUserStatsSerializer()
    orders = DashboardOrderStatsSerializer()
    collection_centers = serializers.IntegerField()


# ══════════════════════════════════════════════════════════
# USER MANAGEMENT SERIALIZERS
# ══════════════════════════════════════════════════════════

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "country_code",
            "role",
            "is_verified",
            "created_at",
        ]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone",
            "role",
            "is_verified",
        ]
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "phone": {"required": False},
            "role": {"required": False},
        }