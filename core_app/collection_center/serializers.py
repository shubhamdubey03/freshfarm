from rest_framework import serializers
from core_app.models import CollectionCenter, CollectionOrder
from core_order.models import Order, Delivery, OrderItem


# ──────────────────────────────────────────
# PROFILE
# ──────────────────────────────────────────

class CollectionCenterProfileSerializer(serializers.ModelSerializer):

    phone = serializers.CharField(source="user.phone", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if not obj.user.profile_image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.user.profile_image.url)
        return obj.user.profile_image.url

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
            "first_name",
            "last_name",
            "image",
        ]
        read_only_fields = ["is_verified"]


class CollectionCenterProfileUpdateSerializer(serializers.ModelSerializer):

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    profile_image = serializers.ImageField(source="user.profile_image", required=False)

    class Meta:
        model = CollectionCenter
        fields = [
            "center_name",
            "address",
            "city",
            "state",
            "latitude",
            "longitude",
            "first_name",
            "last_name",
            "profile_image",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        instance.center_name = validated_data.get("center_name", instance.center_name)
        instance.address = validated_data.get("address", instance.address)
        instance.city = validated_data.get("city", instance.city)
        instance.state = validated_data.get("state", instance.state)
        instance.latitude = validated_data.get("latitude", instance.latitude)
        instance.longitude = validated_data.get("longitude", instance.longitude)
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
    order_status = serializers.CharField(source="order.status", read_only=True)
    farmer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CollectionOrder
        fields = [
            "id",
            "order_id",
            "status",
            "order_status",
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
    order_status = serializers.CharField(source="order.status", read_only=True)
    farmer = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = CollectionOrder
        fields = [
            "id",
            "order_id",
            "status",
            "order_status",
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


# ──────────────────────────────────────────
# PENDING ORDERS (Offline collection)
# ──────────────────────────────────────────

class CollectionPendingOrderSerializer(serializers.ModelSerializer):
    farmer = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "farmer",
            "customer",
            "items",
            "created_at",
        ]

    def get_farmer(self, obj):
        order_item = OrderItem.objects.filter(
            order=obj
        ).select_related("seller__user").first()

        if not order_item or not order_item.seller:
            return None

        return {
            "farm_name": order_item.seller.farm_name,
            "phone": order_item.seller.user.phone,
        }

    def get_customer(self, obj):
        user = obj.user
        address = obj.address
        address_str = ""
        if address:
            city_name = address.city.name if address.city else ""
            address_str = f"{address.address_line}, {city_name}"
        return {
            "name": user.username,
            "phone": user.phone,
            "address": address_str,
        }

    def get_items(self, obj):
        items = OrderItem.objects.filter(order=obj)
        return CollectionOrderItemSerializer(items, many=True).data