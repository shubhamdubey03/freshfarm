from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from .models import Product, ProductVariant,Category
from core_order.models import OrderStatusHistory,Order



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = Product
        fields = '__all__'


class UpdateInventorySerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate(self, data):
        if data["quantity"] <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")

        # ✅ Check variant exists
        try:
            variant = ProductVariant.objects.get(id=data["variant"])
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError("Variant not found")

        data["variant_obj"] = variant
        return data

    @transaction.atomic
    def save(self):
        variant = ProductVariant.objects.select_for_update().get(
            id=self.validated_data["variant"]
        )

        # ✅ Atomic update
        variant.stock = F("stock") + self.validated_data["quantity"]
        variant.save()

        variant.refresh_from_db()
        return variant
class UpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatusHistory.STATUS_CHOICES)

    def validate(self, data):
        order = self.context["order"]
        new_status = data["status"]

        # 🚫 Example rule: can't update if already delivered
        if order.status == "delivered":
            raise serializers.ValidationError("Order already delivered")

        # 🚫 Prevent invalid transitions (optional but powerful 🔥)
        valid_transitions = {
            "at_collection_center": ["out_for_delivery"],
            "out_for_delivery": ["delivered"],
        }

        if order.status in valid_transitions:
            if new_status not in valid_transitions[order.status]:
                raise serializers.ValidationError(
                    f"Invalid status transition from {order.status} → {new_status}"
                )

        return data

    def save(self, **kwargs):
        order = self.context["order"]
        user = self.context["request"].user
        new_status = self.validated_data["status"]

        # ✅ Update order
        order.status = new_status
        order.save()

        # ✅ Create history
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            updated_by=user
        )

        return order