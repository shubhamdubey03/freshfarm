from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core_app.models import Seller
from core_app.vendor.permissions import IsVendor
from core_order.models import (
    VendorOrder,
    Delivery,
    SellerEarning,
    SellerPayout,
    AdminCommission,
    OrderStatusHistory,
)
from core_order.utility import auto_assign_delivery
from core_app.vendor.vendor_serializers import (
    VendorProfileSerializer,
    VendorProfileUpdateSerializer,
    VendorOrderListSerializer,
    VendorOrderDetailSerializer,
    SellerEarningSerializer,
    SellerPayoutSerializer,
)


# ──────────────────────────────────────────
# HELPER — get seller from logged in user
# ──────────────────────────────────────────

def get_vendor_seller(id):
    return get_object_or_404(
        Seller, id=id,seller_type="vendor"
    )


def get_vendor_user(user):
    return get_object_or_404(Seller,user=user,seller_type="vendor")


# ──────────────────────────────────────────
# 1. PROFILE
# ──────────────────────────────────────────

class VendorProfileView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get_object(self, id):
        return get_vendor_seller(id=id)

    def get(self, request,id):
        seller = get_vendor_seller(id)
        serializer = VendorProfileSerializer(seller)
        return Response(serializer.data)

    def delete(self, request,id):
        try:
            seller = get_vendor_seller(id)
        except Seller.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=404)

        seller.delete()

        return Response({
            "message": "Vendor profile deleted successfully"
        })  


    def patch(self, request,id):
        seller = get_vendor_seller(id)
        serializer = VendorProfileUpdateSerializer(
            seller, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated.",
                **serializer.data,
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────
# 2. ORDER LIST
# ──────────────────────────────────────────

class VendorOrderListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        seller =  get_vendor_user(request.user)

        vendor_orders = VendorOrder.objects.filter(
            vendor=seller
        ).select_related(
            "order", "order__user", "order__address"
        ).order_by("-order__created_at")

        # optional filter by status
        order_status = request.query_params.get("status")
        if order_status:
            vendor_orders = vendor_orders.filter(status=order_status)

        serializer = VendorOrderListSerializer(vendor_orders, many=True)
        return Response({
            "count": vendor_orders.count(),
            "results": serializer.data,
        })


# ──────────────────────────────────────────
# 3. ORDER DETAIL
# ──────────────────────────────────────────

class VendorOrderDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request, pk):
        seller = get_vendor_user(request.user)
        vendor_order = get_object_or_404(
            VendorOrder, id=pk, vendor=seller
        )
        serializer = VendorOrderDetailSerializer(vendor_order)
        return Response(serializer.data)


# ──────────────────────────────────────────
# 4. ACCEPT ORDER
# ──────────────────────────────────────────

# ── Step 1: Vendor accepts order ──────────────────────────
class VendorOrderAcceptView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, pk):
        seller = get_vendor_user(request.user)
        vendor_order = get_object_or_404(VendorOrder, id=pk, vendor=seller)

        if vendor_order.status != "assigned":
            return Response(
                {"error": f"Cannot accept. Current status is '{vendor_order.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vendor_order.status = "accepted"
        vendor_order.save()

        OrderStatusHistory.objects.create(
            order=vendor_order.order,
            status="placed",        # order status stays placed
            updated_by=request.user,
        )

        return Response(
            {"message": "Order accepted. Please pack the order."},
            status=status.HTTP_200_OK,
        )


# ── Step 2: Vendor marks order as packed ──────────────────
class VendorOrderPackedView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, pk):
        seller = get_vendor_user(request.user)
        vendor_order = get_object_or_404(VendorOrder, id=pk, vendor=seller)

        if vendor_order.status != "accepted":
            return Response(
                {"error": f"Cannot mark packed. Current status is '{vendor_order.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vendor_order.status = "packed"
        vendor_order.save()

        return Response(
            {"message": "Order marked as packed. Mark ready when delivery boy can pick up."},
            status=status.HTTP_200_OK,
        )


# ── Step 3: Vendor marks ready → delivery boy auto-assigned ─
class VendorOrderReadyView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, pk):
        seller = get_vendor_user(request.user)
        vendor_order = get_object_or_404(VendorOrder, id=pk, vendor=seller)

        # Allow retry if stuck in 'ready' with no delivery assigned
        if vendor_order.status not in ("packed", "ready"):
            return Response(
                {"error": f"Cannot mark ready. Current status is '{vendor_order.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if vendor_order.status == "packed":
            vendor_order.status = "ready"
            vendor_order.save()

        # ── Auto assign nearest delivery boy ───────────────
        delivery, success, error = auto_assign_delivery(vendor_order.order)

        if not success:
            return Response(
                {"error": f"Order marked ready but delivery assignment failed: {error}"},
                status=status.HTTP_200_OK,
            )

        order = vendor_order.order
        print("order1111111",order)

        # ── Seller earning per order item (90%) ────────────
        for order_item in order.orderitem_set.filter(seller=seller):
            item_earning = order_item.price * order_item.quantity * Decimal("0.90")
            SellerEarning.objects.get_or_create(
                seller=seller,
                order=order,
                order_item=order_item,
                defaults={"amount": item_earning},
            )

        # ── Admin commission once per order (10%) ──────────
        commission_amount = order.total_price * Decimal("0.10")
        AdminCommission.objects.get_or_create(
            order=order,
            defaults={
                "vendor": seller,
                "order_total": order.total_price,
                "commission_rate": Decimal("10.00"),
                "commission_amount": commission_amount,
            },
        )

        return Response(
            {
                "message": "Order ready. Delivery boy assigned.",
                "order_id": order.id,
                "vendor_order_status": "ready",
                "order_status": "out_for_delivery",
                "delivery": {
                    "delivery_boy": delivery.delivery_boy.username,
                    "phone": delivery.delivery_boy.phone,
                    "otp": delivery.otp,
                },
            },
            status=status.HTTP_200_OK,
        )
# ──────────────────────────────────────────
# 7. MY EARNINGS
# ──────────────────────────────────────────

class VendorEarningsView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        seller = get_vendor_user(request.user)
        earnings = SellerEarning.objects.filter(
            seller=seller
        ).order_by("-created_at")

        serializer = SellerEarningSerializer(earnings, many=True)
        return Response({
            "count": earnings.count(),
            "results": serializer.data,
        })


# ──────────────────────────────────────────
# 8. EARNINGS SUMMARY
# ──────────────────────────────────────────

class VendorEarningsSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        seller = get_vendor_user(request.user)

        total_earned = SellerEarning.objects.filter(
            seller=seller
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        total_settled = SellerEarning.objects.filter(
            seller=seller, is_settled=True
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return Response({
            "total_earned": str(total_earned),
            "total_settled": str(total_settled),
            "pending_settlement": str(total_earned - total_settled),
        })


# ──────────────────────────────────────────
# 9. PAYOUT HISTORY
# ──────────────────────────────────────────

class VendorPayoutView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        seller = get_vendor_user(request.user)
        payouts = SellerPayout.objects.filter(
            seller=seller
        ).order_by("-start_date")

        serializer = SellerPayoutSerializer(payouts, many=True)
        return Response({
            "count": payouts.count(),
            "results": serializer.data,
        })              