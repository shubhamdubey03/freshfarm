from rest_framework import serializers
from core_app.models import Seller
from core_order.models import VendorOrder, OrderItem, SellerEarning, SellerPayout
from core_product.models import Product, ProductVariant


class VendorProfileSerializer(serializers.ModelSerializer):

    phone = serializers.CharField(source="user.phone", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    profile_image = serializers.ImageField(source="user.profile_image", read_only=True)

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
            "first_name",
            "last_name",
            "profile_image",
            "latitude",
            "longitude",
        ]
        read_only_fields = ["is_verified", "seller_type"]


class VendorProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    profile_image = serializers.ImageField(source="user.profile_image", required=False)

    class Meta:
        model = Seller
        fields = [
            "farm_name",
            "farm_location",
            "bank_account",
            "ifsc_code",
            "first_name",
            "last_name",
            "profile_image",
            "longitude",
            "latitude",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        instance.farm_name = validated_data.get(
            "farm_name", instance.farm_name
        )

        new_location = validated_data.get("farm_location")
        if new_location and new_location != instance.farm_location:
            if "latitude" not in validated_data and "longitude" not in validated_data:
                try:
                    import googlemaps
                    from django.conf import settings
                    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                    result = gmaps.geocode(new_location)
                    if result:
                        loc = result[0]["geometry"]["location"]
                        instance.latitude = round(loc["lat"], 6)
                        instance.longitude = round(loc["lng"], 6)
                except Exception as e:
                    print("Error during backend geocoding in vendor update:", e)

        instance.farm_location = validated_data.get(
            "farm_location", instance.farm_location
        )
        instance.bank_account = validated_data.get(
            "bank_account", instance.bank_account
        )
        instance.ifsc_code = validated_data.get("ifsc_code", instance.ifsc_code)
        
        # Round explicitly to 6 decimal places if provided
        lat = validated_data.get("latitude")
        if lat is not None:
            instance.latitude = round(float(lat), 6)
        
        lng = validated_data.get("longitude")
        if lng is not None:
            instance.longitude = round(float(lng), 6)
            
        instance.save()

        user = instance.user

        if "first_name" in user_data:
            user.first_name = user_data["first_name"]

        if "last_name" in user_data:
            user.last_name = user_data["last_name"]

        if "profile_image" in user_data:
            user.profile_image = user_data["profile_image"]

        user.save()
        return instance


class OrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source="variant.product.name", read_only=True)
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
    payment_type = serializers.CharField(source="order.order_type", read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="order.created_at", read_only=True)

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
    payment_type = serializers.CharField(source="order.order_type", read_only=True)
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
