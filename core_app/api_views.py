import uuid
from decimal import Decimal

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

from core_app.models import User, Address, Seller, Subscription
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
        serializer = SendOTPSerializer(data=request.data)
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
            "productvariant_set"
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
            productvariant__stock__gt=0
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
        items = CartItem.objects.filter(
    user=request.user
        ).filter(
            Q(variant__product__seller__seller_type="vendor") |
            Q(
                variant__product__seller__seller_type="farmer",
                variant__product__seller__is_verified=True
            )
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

        serializer = OrderSerializer(orders, many=True)
        return Response({
            "count":   orders.count(),
            "results": serializer.data,
        })


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, id=pk, user=request.user)
        serializer = OrderSerializer(order)
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
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        payment = Payment.objects.create(
            order = order,
            amount = order.total_price,
            method = method,
            transaction_id = transaction_id,
            status = "pending",
        )

        return Response({
            "payment_id": payment.id,
            "order_id": order.id,
            "amount": str(order.total_price),
            "method": method,
            "transaction_id": transaction_id,
            "gateway_url": f"https://pay.gateway.com/pay?txn={transaction_id}",
        })


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]  

    def post(self, request):
        from core_payment.models import Payment
        transaction_id = request.data.get("transaction_id")
        gateway_status = request.data.get("status")

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if gateway_status == "success":
            payment.status = "paid"
            payment.order.payment_status = "paid"
        else:
            payment.status = "failed"
            payment.order.payment_status = "failed"

        payment.save(update_fields=["status"])
        payment.order.save(update_fields=["payment_status"])

        return Response({
            "message":"Payment recorded.",
            "order_id":payment.order.id,
            "payment_status": payment.order.payment_status,
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