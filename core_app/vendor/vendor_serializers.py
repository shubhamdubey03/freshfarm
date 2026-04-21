from rest_framework import serializers
from core_app.models import Seller
from core_order.models import VendorOrder, OrderItem, SellerEarning, SellerPayout
from core_product.models import Product, ProductVariant


class VendorProfileSerializer(serializers.ModelSerializer):

    phone = serializers.CharField(source="user.phone", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Seller
        fields = [
            "id",
            "farm_name",
            "farm_location",
            "bank_account",
            "ifsc_code",
            "is_verified",
            "seller_type",
            "phone",
            "username",
        ]
        read_only_fields = ["is_verified", "seller_type"]


class VendorProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Seller
        fields = ["farm_location", "bank_account", "ifsc_code"]


class OrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="variant.product.name", read_only=True
    )
    unit = serializers.CharField(source="variant.unit", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_name", "unit", "quantity", "price"]


class VendorOrderListSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    total_price = serializers.DecimalField(
        source="order.total_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    payment_type = serializers.CharField(
        source="order.order_type", read_only=True
    )
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(
        source="order.created_at", read_only=True
    )

    class Meta:
        model = VendorOrder
        fields = [
            "id",
            "order_id",
            "status",
            "total_price",
            "payment_type",
            "customer_name",
            "customer_phone",
            "items",
            "created_at",
        ]

    def get_customer_name(self, obj):
        return obj.order.user.username

    def get_customer_phone(self, obj):
        return obj.order.user.phone

    def get_items(self, obj):
        items = OrderItem.objects.filter(order=obj.order)
        return OrderItemSerializer(items, many=True).data


class VendorOrderDetailSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)
    total_price = serializers.DecimalField(
        source="order.total_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    payment_type = serializers.CharField(
        source="order.order_type", read_only=True
    )
    customer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = VendorOrder
        fields = [
            "id",
            "order_id",
            "status",
            "total_price",
            "payment_type",
            "customer",
            "items",
        ]

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
        return OrderItemSerializer(items, many=True).data


class SellerEarningSerializer(serializers.ModelSerializer):

    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = SellerEarning
        fields = ["id", "order_id", "amount", "is_settled", "created_at"]


class SellerPayoutSerializer(serializers.ModelSerializer):

    class Meta:
        model = SellerPayout
        fields = [
            "id",
            "total_amount",
            "start_date",
            "end_date",
            "is_paid",
            "paid_at",
        ]         
   