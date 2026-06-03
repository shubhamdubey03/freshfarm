from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import F
from django.db import transaction
from core_product.models import CartItem
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import *
from core_app.models import CollectionCenter, User, Address, Seller, VendorOrder
from core_app.utils.fcm import send_notification
from django.shortcuts import get_object_or_404
from core_order.utility import verify_otp, send_otp
from core_app.utils.distance import get_nearest_vendors
from core_app.tasks import assign_next_vendor
from django.core.cache import cache
import json
from rest_framework import status


class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address_id = request.data.get("address")
        order_type = request.data.get("order_type", "pre_order")

        # ── Cart items lo ──────────────────────────
        cart_items = CartItem.objects.select_related(
            "variant__product__category"
        ).filter(user=user)

        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        # ── flow_type automatically decide karo ────
        has_grocery = cart_items.filter(
            variant__product__category__category_type="grocery"
        ).exists()
        flow_type = "vendor" if has_grocery else "farmer"  # ✅ automatic

        address = get_object_or_404(Address, id=address_id, user=user)
        total_price = 0

        with transaction.atomic():

            # ── farmer flow ke liye collection center ──
            center = None
            if flow_type == "farmer":
                from core_app.utils.distance import get_nearest_collection_center
                center = get_nearest_collection_center(address.latitude, address.longitude)

            # ── Order banao ────────────────────────
            order = Order.objects.create(
                user=user,
                address=address,
                collection_center=center,
                status="placed",
                total_price=0,
                order_type=order_type,
                payment_status="pending",
                flow_type=flow_type,  # ✅ variable, string nahi
            )

            OrderStatusHistory.objects.create(
                order=order, status="placed", updated_by=user
            )

            # ── Order Items banao ──────────────────
            for item in cart_items:
                variant = item.variant

                if variant.stock < item.quantity:
                    return Response(
                        {"error": f"Insufficient stock for {variant.product.name}"},
                        status=400,
                    )

                variant.stock = F("stock") - item.quantity
                variant.save()
                variant.refresh_from_db()

                price = variant.price
                total_price += price * item.quantity

                # ✅ seller product ka owner hai
                seller = variant.product.seller  # 'farmer' nahi 'seller' hai field

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    seller=seller,
                    price=price,
                    quantity=item.quantity,
                )

            # ── Payment status ─────────────────────
            if order_type == "paid":
                order.payment_status = "paid"

            order.total_price = total_price

            # ── Flow ke hisaab se status ───────────
            if flow_type == "vendor":
                order.status = "placed"  # ✅ sirf placed — vendor abhi assign hoga
                order.save()

                # ── Nearest vendor dhundo ──────────
                all_vendors = Seller.objects.filter(
                    seller_type="vendor",
                    is_verified=True,
                    latitude__isnull=False,
                    longitude__isnull=False,
                )

                nearest_vendors = get_nearest_vendors(
                    address.latitude, address.longitude, all_vendors, max_distance_km=10
                )

                if not nearest_vendors:
                    # transaction rollback ho jaye
                    raise Exception("Koi vendor available nahi hai aapke area mein.")

                vendor_ids = [v["vendor"].id for v in nearest_vendors]
                first_vendor = nearest_vendors[0]["vendor"]
                remaining_vendors = vendor_ids[1:]

                # ── Redis queue ────────────────────
                queue_key = f"vendor_queue_{order.id}"
                cache.set(queue_key, json.dumps(remaining_vendors), timeout=600)

                # ── VendorOrder banao ──────────────
                VendorOrder.objects.create(
                    order=order,
                    vendor=first_vendor,
                    status="assigned",
                )

                # ── Vendor ko notify karo ──────────
                send_notification(
                    user=first_vendor.user,
                    title="🛒 Naya Order!",
                    body=f"Order #{order.id} aaya hai — {nearest_vendors[0]['distance']} km door. 30 sec mein accept karo!",
                    data={
                        "type": "new_order",
                        "order_id": str(order.id),
                        "distance": str(nearest_vendors[0]["distance"]),
                        "expires_in": "30",
                    },
                )

                # ── 30 sec baad Celery task ────────
                assign_next_vendor.apply_async(args=[order.id], countdown=30)

            else:
                # ── Farmer flow ────────────────────
                order.status = "farmer_assigned"
                order.save()

                OrderStatusHistory.objects.create(
                    order=order, status="at_collection_center", updated_by=None
                )

            cart_items.delete()

        return Response(
            {
                "message": "Order created successfully",
                "data": OrderSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )


class GetOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("orderitem_set__variant__product", "status_history")
            .order_by("-id")
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        try:
            order = Order.objects.get(id=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        serializer = OrderSerializer(order)
        return Response(serializer.data)


# views.py — collection center marks order ready
class MarkOrderReadyView(APIView):
    def patch(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)

        order.status = "at_collection_center"
        order.save()  # ← signal fires here, delivery auto-assigned

        return Response(
            {"message": "Order ready. Delivery boy assigned automatically."}
        )


# views.py — OTP send
class SendOTPView(APIView):
    def post(self, request):
        phone = request.data.get("phone")
        user = get_object_or_404(User, phone=phone)

        _, success, error = send_otp(user)

        if not success:
            return Response({"error": error}, status=400)
        return Response({"message": "OTP sent successfully."})


# views.py — OTP verify
class VerifyOTPView(APIView):
    def post(self, request):
        phone = request.data.get("phone")
        otp_code = request.data.get("otp")
        user = get_object_or_404(User, phone=phone)

        success, error = verify_otp(user, otp_code)

        if not success:
            return Response({"error": error}, status=400)
        return Response({"message": "Phone verified.", "user_id": user.id})
