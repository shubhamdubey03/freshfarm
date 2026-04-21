from rest_framework import serializers
from core_product.models import Product, ProductVariant, Category,CartItem

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "unit", "price", "stock", "harvest_date"]


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(
        source="productvariant_set",  # reverse relation
        many=True,
        read_only=True
    )

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "image",
            "category",
            "category_name",
            "variants"
        ] 

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image"]               


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    price = serializers.DecimalField(source='variant.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'variant', 'product_name', 'price', 'quantity']