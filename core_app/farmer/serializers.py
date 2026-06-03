from rest_framework import serializers
from core_app.models import Seller
from core_product.models import Product, ProductVariant, Category
from core_order.models import FarmerOrder, FarmerOrderBatch, FarmerSalary
from django.db.models import Sum

# ──────────────────────────────────────────
# PROFILE
# ──────────────────────────────────────────


class FarmerProfileSerializer(serializers.ModelSerializer):

    phone = serializers.CharField(source="user.phone", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", read_only=True
    )  # ← add
    last_name = serializers.CharField(source="user.last_name", read_only=True)  # ←
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.user.profile_image and request:
            return request.build_absolute_uri(obj.user.profile_image.url)
        return None

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
            "image",
        ]
        read_only_fields = ["is_verified", "seller_type"]


class FarmerProfileUpdateSerializer(serializers.ModelSerializer):

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    profile_image = serializers.ImageField(source="user.profile_image", required=False)

    class Meta:
        model = Seller
        fields = [
            "farm_location",
            "bank_account",
            "ifsc_code",
            "first_name",
            "last_name",
            "profile_image",
        ]

    def update(self, instance, validated_data):
        # 👇 nested user data alag nikalo
        user_data = validated_data.pop("user", {})

        # 👇 Seller fields update
        instance.farm_location = validated_data.get(
            "farm_location", instance.farm_location
        )
        instance.bank_account = validated_data.get(
            "bank_account", instance.bank_account
        )
        instance.ifsc_code = validated_data.get("ifsc_code", instance.ifsc_code)
        instance.save()

        # 👇 User fields update
        user = instance.user
        print("kkk", user)

        if "first_name" in user_data:
            user.first_name = user_data["first_name"]

        if "last_name" in user_data:
            user.last_name = user_data["last_name"]

        if "profile_image" in user_data:
            user.profile_image = user_data["profile_image"]

        user.save()

        return instance


# ──────────────────────────────────────────
# PRODUCT
# ──────────────────────────────────────────


class ProductVariantSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductVariant
        fields = ["id", "unit", "price", "stock", "harvest_date"]
        read_only_fields = ["price"]  # price set by admin only


class ProductVariantCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductVariant
        fields = ["unit", "stock", "harvest_date"]
        # no price — admin sets it


class ProductListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    category_name = serializers.CharField(source="category.name", read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "image",
            "category",
            "category_name",
            "variants",
            "created_at",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ProductCreateSerializer(serializers.ModelSerializer):

    unit = serializers.CharField(write_only=True)
    stock = serializers.IntegerField(write_only=True)
    harvest_date = serializers.DateField(write_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "image",
            "unit",
            "stock",
            "harvest_date",
        ]

    def create(self, validated_data):
        # pop variant fields
        unit = validated_data.pop("unit")
        stock = validated_data.pop("stock")
        harvest_date = validated_data.pop("harvest_date")

        # create product
        product = Product.objects.create(**validated_data)

        # create variant — price is null until admin sets it
        ProductVariant.objects.create(
            product=product,
            unit=unit,
            stock=stock,
            harvest_date=harvest_date,
            price=0,  # admin will update this
        )

        return product


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Farmer can only update stock and harvest_date.
    Name, description, image, price are read-only for farmer.
    """

    stock = serializers.IntegerField(write_only=True, required=False)
    harvest_date = serializers.DateField(write_only=True, required=False)
    variant_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = ["stock", "harvest_date", "variant_id"]

    def update(self, instance, validated_data):
        stock = validated_data.pop("stock", None)
        harvest_date = validated_data.pop("harvest_date", None)
        variant_id = validated_data.pop("variant_id", None)

        # update variant if provided
        if stock is not None or harvest_date is not None:
            if variant_id:
                variant = ProductVariant.objects.filter(
                    id=variant_id, product=instance
                ).first()
            else:
                variant = instance.variants.first()

            if variant:
                if stock is not None:
                    variant.stock = stock
                if harvest_date is not None:
                    variant.harvest_date = harvest_date
                variant.save()

        return instance


# ──────────────────────────────────────────
# ORDERS
# ──────────────────────────────────────────


class FarmerOrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="order_item.variant.product.name", read_only=True
    )
    unit = serializers.CharField(source="order_item.variant.unit", read_only=True)
    price = serializers.DecimalField(
        source="order_item.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    batch_date = serializers.DateField(source="batch.date", read_only=True)
    batch_cutoff = serializers.DateTimeField(source="batch.cutoff_time", read_only=True)
    batch_is_closed = serializers.BooleanField(source="batch.is_closed", read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = FarmerOrder
        fields = [
            "id",
            "product_name",
            "unit",
            "quantity",
            "price",
            "batch_date",
            "batch_cutoff",
            "batch_is_closed",
            "product_image",
        ]

    def get_product_image(self, obj):
        request = self.context.get("request")
        image = obj.order_item.variant.product.image
        if image and request:
            return request.build_absolute_uri(image.url)
        return None


class FarmerOrderDetailSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="order_item.variant.product.name", read_only=True
    )
    unit = serializers.CharField(source="order_item.variant.unit", read_only=True)
    price = serializers.DecimalField(
        source="order_item.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    batch = serializers.SerializerMethodField()
    deliver_to_center = serializers.SerializerMethodField()

    class Meta:
        model = FarmerOrder
        fields = [
            "id",
            "product_name",
            "unit",
            "quantity",
            "price",
            "batch",
            "deliver_to_center",
        ]

    def get_batch(self, obj):
        return {
            "id": obj.batch.id,
            "date": obj.batch.date,
            "cutoff_time": obj.batch.cutoff_time,
            "is_closed": obj.batch.is_closed,
        }

    def get_deliver_to_center(self, obj):
        # get collection center from order
        center = obj.order_item.order.collection_center
        if not center:
            return None
        return {
            "center_name": center.center_name,
            "address": center.address,
            "city": center.city,
            "latitude": str(center.latitude) if center.latitude else None,
            "longitude": str(center.longitude) if center.longitude else None,
        }


# ──────────────────────────────────────────
# BATCHES
# ──────────────────────────────────────────


class FarmerBatchListSerializer(serializers.ModelSerializer):

    total_items = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()

    class Meta:
        model = FarmerOrderBatch
        fields = [
            "id",
            "date",
            "cutoff_time",
            "is_closed",
            "total_items",
            "total_quantity",
            "created_at",
        ]

    def get_total_items(self, obj):
        return obj.farmerorder_set.count()

    def get_total_quantity(self, obj):
        result = obj.farmerorder_set.aggregate(total=Sum("quantity"))
        return result["total"] or 0


class FarmerBatchDetailSerializer(serializers.ModelSerializer):

    orders = serializers.SerializerMethodField()
    collection_center = serializers.SerializerMethodField()

    class Meta:
        model = FarmerOrderBatch
        fields = [
            "id",
            "date",
            "cutoff_time",
            "is_closed",
            "orders",
            "collection_center",
            "created_at",
        ]

    def get_orders(self, obj):
        farmer = self.context.get("farmer")
        farmer_orders = obj.farmerorder_set.filter(farmer=farmer)
        return [
            {
                "product_name": fo.order_item.variant.product.name,
                "unit": fo.order_item.variant.unit,
                "quantity": fo.quantity,
            }
            for fo in farmer_orders
        ]

    def get_collection_center(self, obj):
        # get from first farmer order in batch
        farmer = self.context.get("farmer")
        first_order = (
            obj.farmerorder_set.filter(farmer=farmer)
            .select_related("order_item__order__collection_center")
            .first()
        )

        if not first_order:
            return None

        center = first_order.order_item.order.collection_center
        if not center:
            return None

        return {
            "center_name": center.center_name,
            "address": center.address,
            "city": center.city,
        }


# ──────────────────────────────────────────
# SALARY
# ──────────────────────────────────────────


class FarmerSalarySerializer(serializers.ModelSerializer):

    month_display = serializers.SerializerMethodField()

    class Meta:
        model = FarmerSalary
        fields = [
            "id",
            "month",
            "month_display",
            "amount",
            "is_paid",
            "paid_at",
            "note",
        ]

    def get_month_display(self, obj):
        return obj.month.strftime("%b %Y")
