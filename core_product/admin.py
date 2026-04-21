# core_product/admin.py

from django.contrib import admin
from core_app.admin import freshapp_admin, green_badge, blue_badge, yellow_badge
from core_product.models import Category, Product, ProductVariant, CartItem


class ProductVariantInline(admin.TabularInline):
    model  = ProductVariant
    extra  = 1
    fields = ["unit", "price", "stock", "harvest_date"]


@admin.register(Category, site=freshapp_admin)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ["name", "category_type_badge"]
    list_filter   = ["category_type"]
    search_fields = ["name"]

    def category_type_badge(self, obj):
        return green_badge("VEGETABLE") if obj.category_type == "vegetable" else blue_badge("GROCERY")
    category_type_badge.short_description = "Type"


@admin.register(Product, site=freshapp_admin)
class ProductAdmin(admin.ModelAdmin):
    list_display    = ["name", "seller", "category", "seller_type_badge", "created_at"]
    list_filter     = ["category", "seller__seller_type"]
    search_fields   = ["name", "seller__farm_name"]
    inlines         = [ProductVariantInline]
    readonly_fields = ["created_at"]

    def seller_type_badge(self, obj):
        return green_badge("FARMER") if obj.seller.seller_type == "farmer" else blue_badge("VENDOR")
    seller_type_badge.short_description = "Seller Type"


@admin.register(ProductVariant, site=freshapp_admin)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display  = ["product", "unit", "price", "stock", "stock_badge", "harvest_date"]
    list_filter   = ["harvest_date"]
    search_fields = ["product__name"]

    def stock_badge(self, obj):
        if obj.stock == 0:
            return yellow_badge("OUT OF STOCK")
        elif obj.stock < 10:
            return yellow_badge(f"LOW ({obj.stock})")
        return green_badge(f"OK ({obj.stock})")
    stock_badge.short_description = "Stock Status"


@admin.register(CartItem, site=freshapp_admin)
class CartItemAdmin(admin.ModelAdmin):
    list_display  = ["user", "variant", "quantity", "created_at"]
    search_fields = ["user__username", "user__phone"]
    date_hierarchy = "created_at"
