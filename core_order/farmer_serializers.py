from rest_framework import serializers
from .models import Order, OrderItem, Delivery
from core_product.models import ProductVariant
from core_app.models import Seller

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    unit = serializers.CharField(source="variant.unit", read_only=True)
    seller_name = serializers.CharField(source="seller.farm_name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "variant",
            "product_name",
            "unit",
            "seller_name",
            "price",
            "quantity"
        ]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "address",
            "collection_center",
            "status",
            "order_type",
            "payment_status",
            "total_price",
            "created_at",
            "items"
        ]
