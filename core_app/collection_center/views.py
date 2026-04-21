from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core_app.models import CollectionCenter, CollectionOrder
from core_app.collection_center.permissions import IsCollectionCenter
from core_app.collection_center.serializers import (
    CollectionCenterProfileSerializer,
    CollectionCenterProfileUpdateSerializer,
    CollectionOrderListSerializer,
    CollectionOrderDetailSerializer,
    CollectionDeliveryListSerializer,
)
from core_order.models import Delivery, Order, OrderStatusHistory
from core_order.utility import auto_assign_delivery


# ──────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────

def get_collection_center(user):
    return get_object_or_404(CollectionCenter, user=user)

# ──────────────────────────────────────────
# 1. PROFILE
# ──────────────────────────────────────────

class CollectionCenterProfileView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def get(self, request):
        center = get_collection_center(request.user)
        serializer = CollectionCenterProfileSerializer(center)
        return Response(serializer.data)

    def patch(self, request):
        center = get_collection_center(request.user)
        serializer = CollectionCenterProfileUpdateSerializer(
            center, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated.",
                **serializer.data,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    def delete(self, request):
        try:
            center = get_collection_center(request.user)
        except CollectionCenter.DoesNotExist:
            return Response({"error": "Collection center not found"}, status=404)

        center.delete()

        return Response({
            "message": "Profile deleted successfully"
        })


# ──────────────────────────────────────────
# 2. INCOMING ORDERS — LIST
# ──────────────────────────────────────────

class CollectionOrderListView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def get(self, request):
        center = get_collection_center(request.user)

        collection_orders = CollectionOrder.objects.filter(
            collection_center=center
        ).select_related(
            "order", "order__user", "order__address"
        ).order_by("-created_at")

        # optional filter
        order_status = request.query_params.get("status")
        if order_status:
            collection_orders = collection_orders.filter(
                status=order_status
            )

        serializer = CollectionOrderListSerializer(
            collection_orders, many=True
        )
        return Response({
            "count": collection_orders.count(),
            "results": serializer.data,
        })


# ──────────────────────────────────────────
# 3. INCOMING ORDERS — DETAIL
# ──────────────────────────────────────────

class CollectionOrderDetailView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def get(self, request, pk):
        center = get_collection_center(request.user)
        collection_order = get_object_or_404(
            CollectionOrder,
            id=pk,
            collection_center=center
        )
        serializer = CollectionOrderDetailSerializer(collection_order)
        return Response(serializer.data)


# ──────────────────────────────────────────
# 4. MARK RECEIVED FROM FARMER
# ──────────────────────────────────────────

class CollectionOrderReceivedView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def post(self, request, pk):
        center = get_collection_center(request.user)
        collection_order = get_object_or_404(
            CollectionOrder,
            id=pk,
            collection_center=center
        )

        # update collection order status
        collection_order.status = "pending"
        collection_order.save()

        # update main order status
        order = collection_order.order
        order.status = "at_collection_center"
        order.save(update_fields=["status"])

        # log status history
        OrderStatusHistory.objects.create(
            order=order,
            status="at_collection_center",
            updated_by=request.user,
        )

        return Response({
            "message": "Order marked as received from farmer.",
            "collection_order_id": collection_order.id,
            "status": collection_order.status,
        })


# ──────────────────────────────────────────
# 5. MARK READY — triggers delivery assignment
# ──────────────────────────────────────────

class CollectionOrderReadyView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def post(self, request, pk):
        center = get_collection_center(request.user)
        collection_order = get_object_or_404(
            CollectionOrder,
            id=pk,
            collection_center=center
        )

        if collection_order.status != "pending":
            return Response(
                {
                    "error": f"Cannot mark ready. "
                             f"Current status is '{collection_order.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # update collection order status
        collection_order.status = "ready"
        collection_order.save()

        # trigger auto delivery assignment
        order = collection_order.order
        delivery, success, error = auto_assign_delivery(order)

        if not success:
            return Response(
                {
                    "error": f"Order marked ready but "
                             f"delivery assignment failed: {error}"
                },
                status=status.HTTP_200_OK,
            )

        # mark collection order as assigned
        collection_order.status = "assigned"
        collection_order.save()

        return Response({
            "message": "Order ready. Delivery boy auto-assigned.",
            "collection_order_id": collection_order.id,
            "status": "assigned",
            "delivery": {
                "delivery_boy": delivery.delivery_boy.username,
                "phone": delivery.delivery_boy.phone,
                "estimated_pickup": "08:00 AM",
            },
        })


# ──────────────────────────────────────────
# 6. LIST DELIVERIES FROM THIS CENTER
# ──────────────────────────────────────────

class CollectionDeliveryListView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def get(self, request):
        center = get_collection_center(request.user)

        deliveries = Delivery.objects.filter(
            pickup_center=center
        ).select_related(
            "order", "delivery_boy"
        ).order_by("-order__created_at")

        serializer = CollectionDeliveryListSerializer(
            deliveries, many=True
        )
        return Response({
            "count": deliveries.count(),
            "results": serializer.data,
        })


# ──────────────────────────────────────────
# 7. VERIFY DELIVERY BOY OTP ON PICKUP
# ──────────────────────────────────────────

class CollectionDeliveryVerifyOTPView(APIView):
    permission_classes = [IsAuthenticated, IsCollectionCenter]

    def post(self, request, pk):
        center = get_collection_center(request.user)
        delivery = get_object_or_404(
            Delivery,
            id=pk,
            pickup_center=center
        )

        if delivery.status != "assigned":
            return Response(
                {
                    "error": f"Cannot verify OTP. "
                             f"Delivery status is '{delivery.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_input =str(request.data.get("otp", "")).strip()

        if not otp_input:
            return Response(
                {"error": "OTP is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery.otp != otp_input:
            return Response(
                {"error": "Invalid OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # mark delivery as picked up
        from django.utils import timezone
        delivery.status = "picked_up"
        delivery.pickup_time = timezone.now()
        delivery.save(update_fields=["status", "pickup_time"])

        # update order status
        order = delivery.order
        order.status = "out_for_delivery"
        order.save(update_fields=["status"])

        # log history
        OrderStatusHistory.objects.create(
            order=order,
            status="out_for_delivery",
            updated_by=request.user,
        )

        return Response({
            "message": "OTP verified. Handover complete.",
            "delivery_id": delivery.id,
            "status": delivery.status,
            "pickup_time": delivery.pickup_time,
        })