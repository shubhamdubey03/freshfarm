from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "product_name", "price", "quantity"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source="orderitem_set", many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "flow_type",
            "address",
            "collection_center",
            "total_price",
            "status",
            "order_type",        
            "payment_status",  
            "created_at",
            "items"
        ]