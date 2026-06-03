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
        product = obj.variant.product
        image = product.image or (product.category.image if product.category else None)
        if image:
            if request:
                return request.build_absolute_uri(image.url)
            return image.url
        return None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source="orderitem_set", many=True, read_only=True)
    address_details = AddressSerializer(source="address", read_only=True)
    delivery_otp = serializers.SerializerMethodField()
    seller_details = serializers.SerializerMethodField()

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
            "address_details",
            "delivery_otp",
            "seller_details"
        ]

    def get_delivery_otp(self, obj):
        try:
            return obj.delivery.otp
        except Exception:
            return None

    def get_seller_details(self, obj):
        seller = None
        if obj.flow_type == "vendor":
            from core_app.models import VendorOrder
            vo = VendorOrder.objects.filter(order=obj).first()
            if vo:
                seller = vo.vendor
        else:
            item = obj.orderitem_set.first()
            if item:
                seller = item.seller
        
        if seller:
            request = self.context.get('request')
            profile_image_url = None
            if seller.user.profile_image:
                if request:
                    profile_image_url = request.build_absolute_uri(seller.user.profile_image.url)
                else:
                    profile_image_url = seller.user.profile_image.url

            return {
                "id": seller.id,
                "farm_name": seller.farm_name,
                "farm_location": seller.farm_location,
                "latitude": str(seller.latitude) if seller.latitude else None,
                "longitude": str(seller.longitude) if seller.longitude else None,
                "first_name": seller.user.first_name,
                "last_name": seller.user.last_name,
                "phone": seller.user.phone,
                "profile_image": profile_image_url,
            }
        return None