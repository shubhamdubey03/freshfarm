import random
import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from rest_framework_simplejwt.tokens import RefreshToken

from core_app.models import User, OTP, Seller, Address, CollectionCenter, Subscription
from core_product.models import Product, ProductVariant, Category, CartItem

User = get_user_model()


# ──────────────────────────────────────────
# REGISTER
# ──────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        max_length=150,
        validators=[]   
    )
    center_name = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    farm_name = serializers.CharField(required=False)
    farm_location = serializers.CharField(required=False)

    class Meta:
        model  = User
        fields = [
            "username",
            "email",
            "phone",
            "role",
            "country_code",
            "center_name",
            "address",
            "farm_name",
            "farm_location",
        ]
        # Username Validation
    def validate_username(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")

        if not re.match(r"^[A-Za-z ]+$", value):
            raise serializers.ValidationError("Username should contain only letters and spaces")

        return value

    # Email Validation
    def validate_email(self, value):
        if value:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already exists")
        return value

    # Phone Validation
    def validate_phone(self, value):
        if not re.match(r"^[6-9]\d{9}$", value):
            raise serializers.ValidationError("Enter valid 10-digit Indian phone number")

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone number already registered")

        return value

    def create(self, validated_data):
        center_name = validated_data.pop("center_name", None)
        address = validated_data.pop("address", None)
        farm_name = validated_data.pop("farm_name", None)
        farm_location = validated_data.pop("farm_location", None)
        role = validated_data["role"]
        
        user = User.objects.create_user(
            username = validated_data["username"],
            email = validated_data.get("email", ""),
            phone = validated_data["phone"],
            role = validated_data["role"],
            country_code = validated_data.get("country_code", "+91"),
            is_verified  = False if role == "farmer" else True 
        )

        if user.role in ["vendor", "farmer"]:
            Seller.objects.create(
                user = user,
                seller_type = user.role,
                farm_name = farm_name or user.username,
                farm_location = farm_location or "",
                bank_account = "",
                ifsc_code = "",
            )

        elif user.role == "collection_center":
            CollectionCenter.objects.create(
                user = user,
                center_name = center_name or user.username,
                address = address or "",
                city = "",
                state = "",
            )

        return user


# ──────────────────────────────────────────
# SEND OTP
# ──────────────────────────────────────────

class SendOTPSerializer(serializers.Serializer):

    country_code = serializers.CharField(max_length=5)
    phone = serializers.CharField(max_length=15)
    def validate(self, data):
        phone = data.get("phone")
        country_code = data.get("country_code")

        try:
            user = User.objects.get(phone=phone, country_code=country_code)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        data["user"] = user
        return data
    def create(self, validated_data):
        user = validated_data["user"]

        # delete old OTPs
        OTP.objects.filter(user=user).delete()

        otp_code = str(random.randint(100000, 999999))

        otp_obj = OTP.objects.create(
            user = user,
            otp = otp_code,
            expire_at = timezone.now() + timedelta(seconds=59),
        )

        # TODO: replace print with real SMS
        print(f"[OTP] {user.phone} → {otp_code}")

        return {
            "message":"OTP sent successfully.",
            "phone":user.phone,
            "expire_at":  otp_obj.expire_at,
            "role":user.role,
        }


# ──────────────────────────────────────────
# VERIFY OTP
# ──────────────────────────────────────────

class VerifyOTPSerializer(serializers.Serializer):

    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        phone = attrs.get("phone")
        otp_code = attrs.get("otp")

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        # delete expired OTPs first
        OTP.objects.filter(
            user=user,
            expire_at__lte=timezone.now()
        ).delete()

        # get latest valid OTP
        otp_obj = OTP.objects.filter(
            user=user,
            expire_at__gte=timezone.now()
        ).order_by("-created_at").first()

        if not otp_obj:
            raise serializers.ValidationError(
                "OTP expired or not found. Please request a new one."
            )

        if otp_obj.otp != otp_code:
            raise serializers.ValidationError("Invalid OTP.")

        attrs["user"] = user
        attrs["otp_obj"] = otp_obj
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        otp_obj = validated_data["otp_obj"]

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        otp_obj.delete()

        refresh = RefreshToken.for_user(user)

        return {
            "access_token":  str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "phone": user.phone,
                "role": user.role,
            },
        }


# ──────────────────────────────────────────
# GOOGLE LOGIN
# ──────────────────────────────────────────

class GoogleLoginSerializer(serializers.Serializer):
    token = serializers.CharField()


# ──────────────────────────────────────────
# TOKEN REFRESH
# ──────────────────────────────────────────

class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        if not attrs.get("refresh"):
            raise serializers.ValidationError("Refresh token is required.")
        return attrs


# ──────────────────────────────────────────
# PROFILE
# ──────────────────────────────────────────

class ProfileSerializer(serializers.ModelSerializer):
    # profile_image = serializers.SerializerMethodField() 
    class Meta:
        model  = User
        fields = ["id", "username", "email", "phone", "role", "is_verified","profile_image"]
        read_only_fields = ["id", "role", "is_verified"]


    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if obj.profile_image and request:
            return request.build_absolute_uri(obj.profile_image.url)
        return None
#     def update(self, instance, validated_data):
#         # ✅ profile_image file handle karo
#         profile_image = self.context['request'].FILES.get('profile_image')
#         if profile_image:
#             instance.profile_image = profile_image
        
#         for attr, value in validated_data.items():
#             if attr != 'profile_image':
#                 setattr(instance, attr, value)
        
#         instance.save()
#         return instance

# # ──────────────────────────────────────────
# ADDRESS
# ──────────────────────────────────────────

class StateSerializer(serializers.ModelSerializer):

    class Meta:
        from core_app.models import State
        model  = State
        fields = ["id", "name", "state_code"]


class CitySerializer(serializers.ModelSerializer):

    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        from core_app.models import City
        model  = City
        fields = ["id", "name", "pincode", "state_name"]


class AddressSerializer(serializers.ModelSerializer):

    city_name  = serializers.CharField(source="city.name",  read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model  = Address
        fields = [
            "id",
            "address_line",
            "city",
            "city_name",
            "state",
            "state_name",
            "pincode",
            "latitude",
            "longitude",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class AddressCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Address
        fields = [
            "address_line",
            "city",
            "state",
            "pincode",
            "latitude",
            "longitude",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        return Address.objects.create(user=user, **validated_data)

# ──────────────────────────────────────────
# VARIANT CREATE / UPDATE
# ──────────────────────────────────────────

def parse_unit_to_grams(unit: str) -> Decimal:
    unit = unit.strip().lower()
    if unit.endswith("kg"):
        return Decimal(unit.replace("kg", "")) * 1000
    elif unit.endswith("g"):
        return Decimal(unit.replace("g", ""))
    else:
        raise ValueError(f"Invalid unit '{unit}'. Use formats like '500g' or '1kg'.")


class ProductVariantCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = ProductVariant
        fields = ["unit", "stock", "harvest_date"]

    def validate_unit(self, value):
        try:
            parse_unit_to_grams(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value.strip().lower()    

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Stock cannot be negative."
            )
        return value


class ProductVariantAdminCreateSerializer(serializers.ModelSerializer):
    """Admin can set price too."""

    class Meta:
        model  = ProductVariant
        fields = ["unit", "price","base_price_per_kg", "stock", "harvest_date"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Stock cannot be negative."
            )
        return value


class ProductStockUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Product
        fields = ["stock_in_kg", "harvest_date"]

    def validate_stock_in_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Stock must be greater than 0.")
        return value    


class ProductVariantUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = ProductVariant
        fields = ["stock", "harvest_date"]


# ──────────────────────────────────────────
# CATEGORY & PRODUCT
# ──────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model  = Category
        fields = ["id", "name", "image"]


class ProductVariantSerializer(serializers.ModelSerializer):

    class Meta:
        model  = ProductVariant
        fields = ["id", "unit", "price", "stock", "harvest_date"]


class ProductListSerializer(serializers.ModelSerializer):

    category = CategorySerializer(read_only=True)
    variants = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = ["id", "name", "description", "image", "category", "variants"]

    def get_variants(self, obj):
      
      variants = obj.variants.filter(
        stock__gt=0,
        price__gt=0        
    ).order_by("price")  
      return ProductVariantSerializer(variants, many=True).data

class ProductDetailSerializer(serializers.ModelSerializer):

    category = CategorySerializer(read_only=True)
    seller   = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "id", "name", "description",
            "image", "category", "seller", "variants",
        ]

    def get_seller(self, obj):
        return {
            "farm_name": obj.seller.farm_name,
            "seller_type": obj.seller.seller_type,
        }

    def get_variants(self, obj):
        return ProductVariantSerializer(
        obj.variants.filter(        # productvariant → variants (related_name)
            stock__gt=0,
            price__gt=0
        ).order_by("price"),
        many=True
    ).data

# ──────────────────────────────────────────
# CART
# ──────────────────────────────────────────

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True
    )

    unit = serializers.CharField(
        source="variant.unit",
        read_only=True
    )

    price = serializers.DecimalField(
        source="variant.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    subtotal = serializers.SerializerMethodField()
    def get_subtotal(self, obj):
        # 🔥 Safe decimal calculation
        return str(Decimal(obj.variant.price) * obj.quantity)
    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant",
            "product_name",
            "unit",
            "price",
            "quantity",
            "subtotal",
            "created_at",
        ]
        read_only_fields = ["created_at"]
    
    


    # def to_representation(self, instance):
    #     """
    #     🔥 Hide item if farmer is not verified
    #     (extra safety, even if someone bypassed filter)
    #     """
    #     seller = instance.variant.product.seller

    #     if seller.seller_type == "farmer" and not seller.is_verified:
    #         return None  # item skip ho jayega

    #     return super().to_representation(instance)
class CartItemCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = CartItem
        fields = ["variant", "quantity"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0."
            )
        return value

    def validate(self, attrs):
        variant = attrs.get("variant")
        quantity = attrs.get("quantity")

        # # 🔥 1. Seller approval check
        # seller = variant.product.seller
        # if not seller.is_verified:
        #     raise serializers.ValidationError(
        #         "This product is not approved by admin yet."
        #     )
        if variant.price <= 0:
            raise serializers.ValidationError("This product is not available yet. Price not set.")

        # 🔥 2. Stock check
        if variant.stock < quantity:
            raise serializers.ValidationError(
                f"Only {variant.stock} items in stock."
            )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        cart_item, created = CartItem.objects.get_or_create(
            user = user,
            variant = validated_data["variant"],
            defaults= {"quantity": validated_data["quantity"]},
        )

        if not created:
            cart_item.quantity += validated_data["quantity"]

            # 🔥 Optional: prevent exceeding stock
            if cart_item.quantity > cart_item.variant.stock:
                raise serializers.ValidationError(
                    f"Only {cart_item.variant.stock} items available."
                )

            cart_item.save()

        return cart_item

class CartItemUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = CartItem
        fields = ["quantity"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0."
            )
        return value


# ──────────────────────────────────────────
# SUBSCRIPTION
# ──────────────────────────────────────────

class SubscriptionSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name", read_only=True
    )

    class Meta:
        model  = Subscription
        fields = [
            "id", "product", "product_name",
            "quantity", "start_date", "end_date", "is_active",
        ]


class SubscriptionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Subscription
        fields = ["product", "quantity", "start_date", "end_date"]

    def validate(self, attrs):
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError(
                "end_date must be after start_date."
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return Subscription.objects.create(user=user, **validated_data)