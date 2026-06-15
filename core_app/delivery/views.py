from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core_app.delivery.permissions import IsDeliveryBoy
from core_app.delivery.serializers import (
    DeliveryListSerializer,
    DeliveryDetailSerializer,
    DeliveryHistorySerializer,
    DeliveryProfileSerializer,
)
from core_order.models import Delivery, Order, OrderStatusHistory
from core_app.models import User

# ──────────────────────────────────────────
# Delivery Profile

# ──────────────────────────────────────────


class DeliveryProfileView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    # GET/delivery/profile/
    def get(self, request):
        serializer = DeliveryProfileSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data)

    # PATCH/delivery/profile/
    def patch(self, request):
        user = request.user
        allowed = {"phone", "email", "first_name", "last_name"}
        data = {k: v for k, v in request.data.items() if k in allowed}

        if "profile_image" in request.FILES:
            user.profile_image = request.FILES["profile_image"]

        for field, value in data.items():
            setattr(user, field, value)
        user.save()
        serializer = DeliveryProfileSerializer(user, context={"request": request})
        return Response(serializer.data)


# ──────────────────────────────────────────
# 1. MY ASSIGNMENTS — LIST
# ──────────────────────────────────────────


class DeliveryAssignmentListView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def get(self, request):
        deliveries = (
            Delivery.objects.filter(delivery_boy=request.user)
            .select_related(
                "order",
                "order__user",
                "order__address__city",
                "pickup_center",
                "vendor__user",
            )
            .order_by("-order__created_at")
        )

        # optional filter
        filter_status = request.query_params.get("status")
        if filter_status:
            deliveries = deliveries.filter(status=filter_status)

        serializer = DeliveryListSerializer(deliveries, many=True)
        return Response(
            {
                "count": deliveries.count(),
                "results": serializer.data,
            }
        )


# ──────────────────────────────────────────
# 2. MY ASSIGNMENTS — DETAIL
# ──────────────────────────────────────────


class DeliveryAssignmentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def get(self, request, pk):
        delivery = get_object_or_404(Delivery, id=pk, delivery_boy=request.user)
        serializer = DeliveryDetailSerializer(delivery)
        return Response(serializer.data)


# ──────────────────────────────────────────
# 2.5. ACCEPT / DECLINE / FCM TOKEN VIEWS
# ──────────────────────────────────────────


class DeliveryAcceptView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, id=pk, delivery_boy=request.user)

        if delivery.status != "assigned":
            return Response(
                {"error": f"Cannot accept. Current status is '{delivery.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.status = "accepted"
        delivery.save(update_fields=["status"])

        return Response(
            {
                "message": "Delivery accepted successfully.",
                "status": delivery.status,
            },
            status=status.HTTP_200_OK,
        )


class DeliveryDeclineView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, id=pk, delivery_boy=request.user)

        if delivery.status != "assigned":
            return Response(
                {"error": f"Cannot decline. Current status is '{delivery.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.core.cache import cache
        from core_order.utility import auto_assign_delivery

        order = delivery.order
        # Cache decline for 5 minutes (300 seconds)
        cache.set(f"declined_delivery_{order.id}_{request.user.id}", True, 300)

        # Delete the delivery assignment
        delivery.delete()

        # Trigger auto-assignment for this order to find the next nearest boy
        new_delivery, success, error = auto_assign_delivery(order)

        return Response(
            {
                "message": "Delivery declined. Re-assignment triggered.",
                "reassigned": success,
                "reassign_error": error if not success else None,
            },
            status=status.HTTP_200_OK,
        )


class DeliveryFCMTokenView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def post(self, request):
        token_str = request.data.get("token", "").strip()
        if not token_str:
            return Response(
                {"error": "Token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from core_app.models import FCMToken
        fcm_token, created = FCMToken.objects.update_or_create(
            user=request.user,
            defaults={"token": token_str},
        )

        return Response(
            {
                "message": "FCM token registered successfully.",
                "token": fcm_token.token,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────
# 3. MARK PICKED UP
# ──────────────────────────────────────────


class DeliveryPickedUpView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, id=pk, delivery_boy=request.user)

        if delivery.status != "accepted":
            return Response(
                {
                    "error": f"Cannot mark as picked up. "
                    f"Current status is '{delivery.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_input = str(request.data.get("otp", "")).strip()
        if not otp_input:
            return Response(
                {"error": "OTP is required to start the trip."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery.otp != otp_input:
            return Response(
                {"error": "Invalid OTP. Cannot start trip."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.status = "picked_up"
        delivery.pickup_time = timezone.now()
        delivery.save(update_fields=["status", "pickup_time"])

        # Update order status to out_for_delivery
        order = delivery.order
        order.status = "out_for_delivery"
        order.save(update_fields=["status"])

        # Log status history
        OrderStatusHistory.objects.create(
            order=order,
            status="out_for_delivery",
            updated_by=request.user,
        )

        return Response(
            {
                "message": "OTP verified. Trip started successfully.",
                "delivery_id": delivery.id,
                "status": delivery.status,
                "pickup_time": delivery.pickup_time,
            }
        )


# ──────────────────────────────────────────
# 4. MARK DELIVERED — verify customer OTP
# ──────────────────────────────────────────


class DeliveryDeliveredView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, id=pk, delivery_boy=request.user)

        if delivery.status != "picked_up":
            return Response(
                {
                    "error": f"Cannot mark as delivered. "
                    f"Current status is '{delivery.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_input = str(request.data.get("otp", "")).strip()
        payment_collected = request.data.get("payment_collected", False)
        payment_method = request.data.get("payment_method", "cod")

        if not otp_input:
            return Response(
                {"error": "OTP is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery.otp != otp_input:
            return Response(
                {"error": "Invalid OTP. Cannot mark as delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # mark delivery done
        delivery.status = "delivered"
        delivery.delivery_time = timezone.now()
        delivery.save(update_fields=["status", "delivery_time"])

        # update order
        order = delivery.order
        order.status = "delivered"

        # update payment if COD
        if payment_collected and order.order_type == "cod":
            order.payment_status = "paid"

        order.save(update_fields=["status", "payment_status"])

        # log status history
        OrderStatusHistory.objects.create(
            order=order,
            status="delivered",
            updated_by=request.user,
        )

        # create payment record if COD collected
        if payment_collected and order.order_type == "cod":
            from core_payment.models import Payment

            Payment.objects.get_or_create(
                order=order,
                defaults={
                    "amount": order.total_price,
                    "method": "cod",
                    "transaction_id": f"COD-{order.id}-{timezone.now().timestamp():.0f}",
                    "status": "paid",
                },
            )

        return Response(
            {
                "message": "Order delivered successfully.",
                "delivery_id": delivery.id,
                "status": delivery.status,
                "delivery_time": delivery.delivery_time,
                "payment_status": order.payment_status,
            }
        )


# 4.5. MARK RETURNED — verify customer return photo
# ──────────────────────────────────────────


class DeliveryReturnedView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, id=pk, delivery_boy=request.user)

        if delivery.status != "picked_up":
            return Response(
                {
                    "error": f"Cannot mark as returned. "
                    f"Current status is '{delivery.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "return_image" not in request.FILES:
            return Response(
                {"error": "Return verification photo is mandatory."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.return_image = request.FILES["return_image"]
        delivery.status = "returned"
        delivery.delivery_time = timezone.now()
        delivery.save()

        order = delivery.order
        order.status = "returned"
        order.save(update_fields=["status"])

        OrderStatusHistory.objects.create(
            order=order,
            status="returned",
            updated_by=request.user,
        )

        return Response(
            {
                "message": "Order marked as returned successfully.",
                "delivery_id": delivery.id,
                "status": delivery.status,
            }
        )


# ──────────────────────────────────────────
# 5. DELIVERY HISTORY
# ──────────────────────────────────────────


class DeliveryHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def get(self, request):
        deliveries = Delivery.objects.filter(
            delivery_boy=request.user, status__in=["delivered", "returned"]
        ).order_by("-delivery_time")

        serializer = DeliveryHistorySerializer(deliveries, many=True)
        return Response(
            {
                "count": deliveries.count(),
                "results": serializer.data,
            }
        )


# ──────────────────────────────────────────
# 6. MY EARNINGS
# ──────────────────────────────────────────


class DeliveryEarningsView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def get(self, request):
        total_deliveries = Delivery.objects.filter(
            delivery_boy=request.user, status="delivered"
        ).count()

        # fixed ₹100 per delivery — adjust as needed
        per_delivery_rate = Decimal("100.00")
        total_earned = per_delivery_rate * total_deliveries

        # this month
        now = timezone.now()
        this_month_count = Delivery.objects.filter(
            delivery_boy=request.user,
            status="delivered",
            delivery_time__year=now.year,
            delivery_time__month=now.month,
        ).count()
        this_month_earned = per_delivery_rate * this_month_count

        return Response(
            {
                "total_deliveries": total_deliveries,
                "total_earned": str(total_earned),
                "this_month": str(this_month_earned),
                "per_delivery_rate": str(per_delivery_rate),
            }
        )


# ──────────────────────────────────────────
# 7. UPDATE MY LOCATION
# ──────────────────────────────────────────


class DeliveryLocationUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryBoy]

    def patch(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        if not latitude or not longitude:
            return Response(
                {"error": "Both latitude and longitude are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # update delivery boy's first address coordinates
        address = request.user.user_address.first()

        if not address:
            from core_app.models import City, State, Address
            default_city = City.objects.first()
            default_state = State.objects.first()
            if default_city and default_state:
                address = Address.objects.create(
                    user=request.user,
                    address_line="Default Delivery Location",
                    city=default_city,
                    state=default_state,
                    pincode="201301",
                    latitude=latitude,
                    longitude=longitude,
                )
            else:
                return Response(
                    {"error": "No address found and cannot auto-create because City/State is missing."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            address.latitude = latitude
            address.longitude = longitude
            address.save(update_fields=["latitude", "longitude"])

        return Response(
            {
                "message": "Location updated.",
                "latitude": str(latitude),
                "longitude": str(longitude),
            }
        )
