from rest_framework import serializers
from .models import Order, OrderItem
from core_app.user_serializers import AddressSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "product_name", "product_image", "price", "quantity"]

    def get_product_image(self, obj):
        request = self.context.get('request')
        if obj.variant.product.image:
            if request:
                return request.build_absolute_uri(obj.variant.product.image.url)
            return obj.variant.product.image.url
        return None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source="orderitem_set", many=True, read_only=True)
    address_details = AddressSerializer(source="address", read_only=True)

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
            "items",
            "address_details"
        ]