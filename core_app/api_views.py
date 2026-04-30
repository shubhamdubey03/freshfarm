import uuid
from decimal import Decimal
import googlemaps
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from google.auth.transport import requests
from google.oauth2 import id_token
import razorpay
import hmac
import hashlib
import os
from django.conf import settings

client = razorpay.Client(
    auth=(os.environ.get("RAZORPAY_KEY"), os.environ.get("RAZORPAY_SECRET"))
)

gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

from core_app.models import User, Address, Seller, Subscription,City,State
from core_app.user_serializers import (
    RegisterSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    GoogleLoginSerializer,
    TokenRefreshSerializer,
    ProfileSerializer,
    AddressSerializer,
    AddressCreateSerializer,
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    CartItemSerializer,
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    ProductVariantSerializer,
    ProductVariantUpdateSerializer,
    ProductVariantAdminCreateSerializer,
    ProductVariantCreateSerializer
)
from core_product.models import Product, Category, CartItem, ProductVariant
from core_order.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    FarmerOrder,
    FarmerOrderBatch,
    
)
from core_order.serializers import OrderSerializer
from core_app.models import CollectionCenter,VendorOrder
from core_payment.models import Payment

GOOGLE_CLIENT_ID = "957154860735-1582fvgetnfjqle730eth5a9gcponrfp.apps.googleusercontent.com"


# ══════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        print("serilizers",serializer,request)
        if serializer.is_valid():
           user= serializer.save()
           if user.role == "farmer":
                message = "Registered successfully. Please wait for admin approval before login."
           else:
                message = "User registered successfully. You can login now."

           return Response(
                {"message": message, "role":user.role},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class SendOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        print("------00000000000000")
        serializer = SendOTPSerializer(data=request.data)
        print("ooo",serializer)
        if serializer.is_valid():
            phone = serializer.validated_data.get("phone","country_code")
            country_code = serializer.validated_data.get("country_code", "+91")
            user = User.objects.filter(phone=phone,country_code=country_code).first()
            if user and user.role == "farmer" and not user.is_verified:
                return Response(
                    {"error": "Your account is pending admin approval."},
                    status=403
                )
            data = serializer.save()
            return Response(data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyOTPLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                GOOGLE_CLIENT_ID,
            )
            email = idinfo["email"]
            name  = idinfo.get("name", "")
        except ValueError:
            return Response(
                {"error": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "role":"user",
            },
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access_token":  str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role,
            },
        })


class TokenRefreshAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token= RefreshToken(serializer.validated_data["refresh"])
            access_token = str(token.access_token)
            return Response({"access": access_token})
        except TokenError:
            return Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logout successful."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except Exception:
            return Response(
                {"error": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ══════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════

class GetProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user,context={'request': request})
        return Response(serializer.data)


class UpdateProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def patch(self, request):
        user = request.user
        data = request.data.copy()

        # handle image separately (optional but safer)
        image = request.FILES.get('profile_image')
        if image:
                data['profile_image'] = image

        serializer = ProfileSerializer(
            user,
            data=data,
            partial=True,
            context={'request': request} 
        )

        if serializer.is_valid():
            serializer.save()

            # return full image URL (important for frontend)
            response_data = serializer.data
            if user.profile_image:
                request = self.request
                response_data['profile_image'] = request.build_absolute_uri(user.profile_image.url)

            return Response({
                "message": "Profile updated successfully.",
                "data": response_data
            }, status=status.HTTP_200_OK)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class DeleteProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):

        # 🔒 Optional: Only allow self-delete OR admin
        if request.user.id != user_id and request.user.role != "admin":
            return Response(
                {"error": "You are not allowed to delete this user"},
                status=status.HTTP_403_FORBIDDEN
            )

        user = get_object_or_404(User, id=user_id)
        user.delete()

        return Response(
            {"message": "Account deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

# ══════════════════════════════════════════
# ADDRESS
# ══════════════════════════════════════════

class AddressListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(
            user=request.user
        ).order_by("-created_at")
        serializer = AddressSerializer(addresses, many=True)
        return Response({
            "count":   addresses.count(),
            "results": serializer.data,
        })

    def post(self, request):
        serializer = AddressCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            address = serializer.save()
            return Response(
                AddressSerializer(address).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        address = get_object_or_404(Address, id=pk, user=request.user)
        serializer = AddressSerializer(
            address,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Address updated successfully.",
                "data": serializer.data,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk):
        address = get_object_or_404(Address, id=pk, user=request.user)
        address.delete()
        return Response(
            {"message": "Address deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def geocode_address(request):
    """Convert address text → lat/lng using Google Maps"""
    address_text = request.data.get("address")
    if not address_text:
        return Response({"error": "Address is required"}, status=400)

    result = gmaps.geocode(address_text)
    if not result:
        return Response({"error": "Address not found"}, status=404)

    location = result[0]["geometry"]["location"]
    formatted = result[0]["formatted_address"]

    # Extract components
    components = result[0]["address_components"]
    city_name, state_name, pincode = "", "", ""

    for comp in components:
        if "locality" in comp["types"]:
            city_name = comp["long_name"]
        if "administrative_area_level_1" in comp["types"]:
            state_name = comp["long_name"]
        if "postal_code" in comp["types"]:
            pincode = comp["long_name"]

    return Response({
        "latitude": location["lat"],
        "longitude": location["lng"],
        "formatted_address": formatted,
        "city": city_name,
        "state": state_name,
        "pincode": pincode,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reverse_geocode(request):
    """Convert lat/lng → address"""
    lat = request.data.get("latitude")
    lng = request.data.get("longitude")

    if not lat or not lng:
        return Response({"error": "lat/lng required"}, status=400)

    result = gmaps.reverse_geocode((lat, lng))
    if not result:
        return Response({"error": "Location not found"}, status=404)

    formatted = result[0]["formatted_address"]
    components = result[0]["address_components"]
    city_name, state_name, pincode = "", "", ""

    for comp in components:
        if "locality" in comp["types"]:
            city_name = comp["long_name"]
        if "administrative_area_level_1" in comp["types"]:
            state_name = comp["long_name"]
        if "postal_code" in comp["types"]:
            pincode = comp["long_name"]

    return Response({
        "formatted_address": formatted,
        "city": city_name,
        "state": state_name,
        "pincode": pincode,
    })



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_address(request):
    data = request.data
    user = request.user

    address_line = data.get("address_line", "").strip()
    city_name = data.get("city", "").strip()
    state_name  = data.get("state", "").strip()
    pincode = data.get("pincode", "").strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    # ✅ Validate required fields before touching the DB
    if not state_name:
        return Response({"error": "State name is required. Location may not have been resolved correctly."}, status=400)

    if not city_name:
        return Response({"error": "City name is required."}, status=400)

    if not address_line:
        return Response({"error": "Address line is required."}, status=400)

    if not latitude or not longitude:
        return Response({"error": "Latitude and longitude are required."}, status=400)

    # ✅ Safe get_or_create with proper defaults
    state, _ = State.objects.get_or_create(
        name=state_name,
        defaults={"state_code": state_name[:10]}
    )

    city, _ = City.objects.get_or_create(
        name=city_name,
        state=state,
        defaults={"pincode": pincode}
    )

    address = Address.objects.create(
        user=user,
        address_line=address_line,
        city=city,
        state=state,
        pincode=pincode,
        latitude=latitude,
        longitude=longitude,
    )

    return Response({
        "id": address.id,
        "address_line": address.address_line,
        "city": city.name,
        "state": state.name,
        "pincode": address.pincode,
        "latitude": str(address.latitude),
        "longitude":  str(address.longitude),
    }, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_addresses(request):
    """List all saved addresses of the user"""
    addresses = Address.objects.filter(user=request.user).select_related("city", "state")
    data = [
        {
            "id": a.id,
            "address_line": a.address_line,
            "city": a.city.name,
            "state": a.state.name,
            "pincode": a.pincode,
            "latitude": str(a.latitude),
            "longitude": str(a.longitude),
        }
        for a in addresses
    ]
    return Response(data)
# ──────────────────────────────────────────
# PRODUCT VARIANT DETAIL
# ──────────────────────────────────────────

class ProductVariantListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, product_pk):
        product  = get_object_or_404(Product, id=product_pk)
        variants = ProductVariant.objects.filter(
            product=product,
            stock__gt=0  # only show in-stock variants
        )
        serializer = ProductVariantSerializer(variants, many=True)
        return Response({
            "product_id": product.id,
            "product_name": product.name,
            "count": variants.count(),
            "variants": serializer.data,
        })


class ProductVariantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, product_pk, variant_pk):
        product = get_object_or_404(Product, id=product_pk)
        variant = get_object_or_404(
            ProductVariant,
            id=variant_pk,
            product=product
        )
        return Response({
            "id": variant.id,
            "product_id": product.id,
            "product_name": product.name,
            "unit": variant.unit,
            "price": str(variant.price),
            "stock": variant.stock,
            "harvest_date": variant.harvest_date,
        })    
    
# ──────────────────────────────────────────
# VARIANT CREATE (farmer creates for own product)
# ──────────────────────────────────────────

class ProductVariantCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_pk):

        # get product — farmer can only add variant to own product
        if request.user.role == "farmer":
            seller  = get_object_or_404(
                Seller,
                user=request.user,
                seller_type="farmer"
            )
            product = get_object_or_404(
                Product,
                id=product_pk,
                farmer=seller
            )
            serializer = ProductVariantCreateSerializer(
                data=request.data
            )

        elif request.user.role == "admin":
            product = get_object_or_404(Product, id=product_pk)
            serializer = ProductVariantAdminCreateSerializer(
                data=request.data
            )

        else:
            return Response(
                {"error": "You do not have permission to add variants."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if serializer.is_valid():
            variant = serializer.save(
                product=product,
                price=0  # default 0, admin sets later if farmer created
                if request.user.role == "farmer"
                else serializer.validated_data.get("price", 0),
            )
            return Response(
                {
                    "message": "Variant added successfully.",
                    "product_id": product.id,
                    "product_name": product.name,
                    "variant": {
                        "id": variant.id,
                        "unit": variant.unit,
                        "price": str(variant.price),
                        "stock": variant.stock,
                        "harvest_date": variant.harvest_date,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ──────────────────────────────────────────
# VARIANT UPDATE / DELETE
# ──────────────────────────────────────────

class ProductVariantManageView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, product_pk, variant_pk):

        product = get_object_or_404(Product, id=product_pk)

        # farmer can only update own product variants
        if request.user.role == "farmer":
            seller = get_object_or_404(
                Seller,
                user=request.user,
                seller_type="farmer"
            )
            if product.farmer != seller:
                return Response(
                    {"error": "You can only update your own product variants."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer_class = ProductVariantUpdateSerializer

        elif request.user.role == "admin":
            # admin can update everything including price
            serializer_class = ProductVariantAdminCreateSerializer

        else:
            return Response(
                {"error": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        variant    = get_object_or_404(
            ProductVariant,
            id=variant_pk,
            product=product
        )
        serializer = serializer_class(
            variant,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Variant updated successfully.",
                "variant": {
                    "id": variant.id,
                    "unit": variant.unit,
                    "price": str(variant.price),
                    "stock": variant.stock,
                    "harvest_date": variant.harvest_date,
                },
            })

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, product_pk, variant_pk):

        product = get_object_or_404(Product, id=product_pk)

        # farmer can only delete own product variants
        if request.user.role == "farmer":
            seller = get_object_or_404(
                Seller,
                user=request.user,
                seller_type="farmer"
            )
            if product.farmer != seller:
                return Response(
                    {"error": "You can only delete your own product variants."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        elif request.user.role != "admin":
            return Response(
                {"error": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        variant = get_object_or_404(
            ProductVariant,
            id=variant_pk,
            product=product
        )
        variant.delete()

        return Response(
            {"message": "Variant deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )    
    
# ══════════════════════════════════════════
# PRODUCTS & CATEGORIES
# ══════════════════════════════════════════

class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response({"results": serializer.data})


class ProductListView(APIView):
    permission_classes = [AllowAny]
    print("llll----------------------------------")
    def get(self, request):

        # 🔥 Base queryset (Farmer verified OR Vendor)
        products = Product.objects.filter(
            Q(seller__seller_type="vendor") |
            Q(
                seller__seller_type="farmer",
                seller__user__is_verified=True
            )
        ).select_related(
            "category", "seller"
        ).prefetch_related(
            "variants"
        )

        # 🔹 Category filter
        category_id = request.query_params.get("category")
        if category_id:
            products = products.filter(category_id=category_id)

        # 🔹 Search filter
        search = request.query_params.get("search")
        if search:
            products = products.filter(name__icontains=search)

        # 🔹 Optional: only show products with stock
        products = products.filter(
            variants__stock__gt=0
        ).distinct()

        # 🔹 Ordering
        products = products.order_by("-created_at")

        serializer = ProductListSerializer(products, many=True)

        return Response({
            "count": products.count(),
            "results": serializer.data,
        })

class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        product = get_object_or_404(
            Product.objects.filter(
                Q(seller__seller_type="vendor") |   
                Q(
                    seller__seller_type="farmer",
                    seller__is_verified=True        
                )
            ).select_related(
                "category", "seller"
            ).prefetch_related(
                "productvariant"
            ),
            id=pk,
        )

        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)
# ══════════════════════════════════════════
# CART
# ══════════════════════════════════════════

class CartListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = CartItem.objects.filter(user=request.user).select_related(
            "variant", "variant__product"
        )

        serializer = CartItemSerializer(items, many=True)
        total = sum(
            item.variant.price * item.quantity for item in items
        )
        return Response({
            "items": serializer.data,
            "total": str(total),
        })

    def post(self, request):
        print("request",request)
        serializer = CartItemCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            cart_item = serializer.save()
            return Response(
                CartItemSerializer(cart_item).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        cart_item = get_object_or_404(CartItem, id=pk, user=request.user)
        serializer = CartItemUpdateSerializer(
            cart_item, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(CartItemSerializer(cart_item).data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk):
        cart_item = get_object_or_404(CartItem, id=pk, user=request.user)
        cart_item.delete()
        return Response(
            {"message": "Item removed from cart."},
            status=status.HTTP_204_NO_CONTENT,
        )


# ══════════════════════════════════════════
# ORDERS
# ══════════════════════════════════════════

class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address_id = request.data.get("address")
        order_type = request.data.get("order_type", "pre_order")

        cart_items = CartItem.objects.select_related(
            "variant__product__seller"
        ).filter(user=user)

        if not cart_items.exists():
            return Response(
                {"error": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        address = get_object_or_404(Address, id=address_id, user=user)

        # ── Auto-detect flow_type from cart ───────────────
        sellers = [item.variant.product.seller for item in cart_items]
        has_vendor = any(s.seller_type == "vendor" for s in sellers)
        flow_type = "vendor" if has_vendor else "farmer"

        # ── Collection center only for farmer flow ─────────
        center = None
        if flow_type == "farmer":
            center = CollectionCenter.objects.first()
            if not center:
                return Response(
                    {"error": "No collection center available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        total_price = Decimal("0.00")
        order_items_created = []

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                address=address,
                collection_center=center,   # None for vendor flow
                status="placed",
                total_price=Decimal("0.00"),
                order_type=order_type,
                payment_status="pending",
                flow_type=flow_type,
            )

            OrderStatusHistory.objects.create(
                order=order,
                status="placed",
                updated_by=user,
            )

            for item in cart_items:
                variant = item.variant

                if variant.stock < item.quantity:
                    raise Exception(
                        f"Insufficient stock for {variant.product.name}."
                    )

                variant.stock = F("stock") - item.quantity
                variant.save()
                variant.refresh_from_db()

                price = variant.price
                total_price += price * item.quantity
                seller = variant.product.seller

                order_item = OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    seller=seller,
                    price=price,
                    quantity=item.quantity,
                )
                order_items_created.append((order_item, seller))
                if seller.seller_type == "farmer":
                    # get or create batch
                    batch, _ = FarmerOrderBatch.objects.get_or_create(
                        date=timezone.now().date(),
                        defaults={
                            "cutoff_time": timezone.now() + timedelta(hours=2)
                        }
                    )

                    FarmerOrder.objects.create(
                        order_item=order_item,
                        farmer=seller,
                        batch=batch,
                        quantity=item.quantity,
                    )

            if order_type == "paid":
                order.payment_status = "paid"

            # ── Farmer flow: assign to farmer ──────────────
            # ── Vendor flow: just placed, wait for vendor to accept ──
            order.status = "farmer_assigned" if flow_type == "farmer" else "placed"
            order.total_price = total_price
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                updated_by=None,
            )

            # ── Create VendorOrder, wait for vendor to accept ─
            if flow_type == "vendor":
                vendor_seller = next(
                    (s for _, s in order_items_created if s.seller_type == "vendor"),
                    None
                )
                if not vendor_seller:
                    raise Exception("No vendor seller found in cart items.")

                VendorOrder.objects.create(
                    order=order,
                    vendor=vendor_seller,
                    status="assigned",  # vendor must manually accept
                )

                # ── Notify vendor (like Uber/Ola) ──────────
                # _notify_vendor(vendor_seller, order)  # uncomment when ready

            cart_items.delete()

        return Response(
            {
                "message": "Order created successfully.",
                "flow_type": flow_type,
                "data": OrderSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )

class GetOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related(
            "orderitem_set__variant__product",
            "status_history",
        ).order_by("-id")

        # optional filter
        order_status = request.query_params.get("status")
        if order_status:
            orders = orders.filter(status=order_status)

        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response({
            "count":   orders.count(),
            "results": serializer.data,
        })


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, id=pk, user=request.user)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)


class CancelOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    CANCELLABLE_STATUSES = ["placed", "farmer_assigned"]

    def post(self, request, pk):
        order = get_object_or_404(Order, id=pk, user=request.user)

        if order.status not in self.CANCELLABLE_STATUSES:
            return Response(
                {
                    "error": f"Order cannot be cancelled. "
                             f"Current status is '{order.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # restore stock
            for item in OrderItem.objects.filter(order=order):
                item.variant.stock += item.quantity
                item.variant.save(update_fields=["stock"])

            order.status = "cancelled"
            order.save(update_fields=["status"])

            OrderStatusHistory.objects.create(
                order      = order,
                status     = "cancelled",
                updated_by = request.user,
            )

        return Response({
            "message":  "Order cancelled successfully.",
            "order_id": order.id,
            "status":   "cancelled",
        })


# ══════════════════════════════════════════
# PAYMENT
# ══════════════════════════════════════════

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = get_object_or_404(
            Order,
            id=request.data.get("order_id"),
            user=request.user,
        )

        if order.payment_status == "paid":
            return Response(
                {"error": "Order is already paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        method = request.data.get("method", "upi")

        # ✅ Create Razorpay order
        razorpay_order = client.order.create({
            "amount": int(float(order.total_price) * 100),  # paise
            "currency": "INR",
            "receipt": f"order_{order.id}",
            "payment_capture": 1, 
        })

        payment = Payment.objects.create(
            order=order,
            amount=order.total_price,
            method=method,
            transaction_id=razorpay_order["id"],  # store razorpay order id
            status="pending",
        )

        return Response({
            "payment_id": payment.id,
            "order_id": order.id,
            "amount": int(float(order.total_price) * 100),  # paise for frontend
            "razorpay_order_id": razorpay_order["id"],
            "key_id": os.environ.get("RAZORPAY_KEY"),  # safe to send to frontend
            "method": method,
        })

class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id   = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature  = request.data.get("razorpay_signature")

        # ✅ Verify signature
        body = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_signature = hmac.new(
            os.environ.get("RAZORPAY_SECRET").encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected_signature != razorpay_signature:
            return Response(
                {"error": "Invalid payment signature"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Update payment and order status
        try:
            payment = Payment.objects.get(transaction_id=razorpay_order_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found."}, status=404)

        payment.status = "paid"
        payment.order.payment_status = "paid"
        payment.save(update_fields=["status"])
        payment.order.save(update_fields=["payment_status"])

        return Response({
            "message": "Payment verified successfully.",
            "order_id": payment.order.id,
            "payment_status": "paid",
        })
# ══════════════════════════════════════════
# SUBSCRIPTION
# ══════════════════════════════════════════

class SubscriptionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscriptions = Subscription.objects.filter(
            user=request.user,
            is_active=True,
        ).select_related("product").order_by("-start_date")

        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response({
            "count":   subscriptions.count(),
            "results": serializer.data,
        })

    def post(self, request):
        serializer = SubscriptionCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            subscription = serializer.save()
            return Response(
                SubscriptionSerializer(subscription).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        subscription = get_object_or_404(
            Subscription, id=pk, user=request.user
        )

        if not subscription.is_active:
            return Response(
                {"error": "Subscription is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.is_active = False
        subscription.save(update_fields=["is_active"])

        return Response({
            "message":         "Subscription cancelled.",
            "subscription_id": subscription.id,
        })