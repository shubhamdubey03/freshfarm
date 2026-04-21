# core_app/admin_views.py

from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from core_app.models import User, Seller, CollectionCenter
from core_order.models import Order
from core_app.admins.serializers import (
    FarmerListSerializer,
    FarmerApproveSerializer,
    VendorListSerializer,
    CollectionCenterSerializer,
    CollectionCenterCreateSerializer,
    AdminOrderSerializer,
    DashboardSerializer,
    AdminUserListSerializer,
    AdminUserUpdateSerializer,
)


# ── Permission helper ──────────────────────────────────────
def is_admin(request):
    if request.user.role != "admin":
        return Response(
            {"error": "Admin access required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

class AdminDashboardView(APIView):
    """GET  /api/admin/dashboard/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        data = {
            "users": {
                "total": User.objects.count(),
                "farmers_pending":  User.objects.filter(role="farmer", is_verified=False).count(),
                "farmers_approved": User.objects.filter(role="farmer", is_verified=True).count(),
                "vendors_pending": User.objects.filter(role="vendor", is_verified=False).count(),
                "vendors_approved": User.objects.filter(role="vendor", is_verified=True).count(),
                "delivery_boys": User.objects.filter(role="delivery").count(),
            },
            "orders": {
                "total": Order.objects.count(),
                "placed": Order.objects.filter(status="placed").count(),
                "delivered": Order.objects.filter(status="delivered").count(),
                "cancelled": Order.objects.filter(status="cancelled").count(),
                "revenue": Order.objects.filter(
                    payment_status="paid"
                ).aggregate(t=Sum("total_price"))["t"] or 0,
            },
            "collection_centers": CollectionCenter.objects.count(),
        }

        serializer = DashboardSerializer(data)
        return Response(serializer.data)


# ══════════════════════════════════════════════════════════
# FARMER MANAGEMENT
# ══════════════════════════════════════════════════════════

class AdminPendingFarmersView(APIView):
    """GET  /api/admin/farmers/pending/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        farmers = User.objects.filter(
            role="farmer",
            is_verified=False,
        ).select_related("seller").order_by("-created_at")

        serializer = FarmerListSerializer(farmers, many=True)
        return Response({
            "count":   farmers.count(),
            "results": serializer.data,
        })


class AdminAllFarmersView(APIView):
    """GET  /api/admin/farmers/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        farmers = User.objects.filter(
            role="farmer",
            is_verified=True,
        ).select_related("seller").order_by("-created_at")

        serializer = FarmerListSerializer(farmers, many=True)
        return Response({
            "count":   farmers.count(),
            "results": serializer.data,
        })


class AdminApproveFarmerView(APIView):
    """
    POST /api/admin/farmers/<user_id>/approve/
    POST /api/admin/farmers/<user_id>/reject/
    POST /api/admin/farmers/<user_id>/revoke/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id, action):
        err = is_admin(request)
        if err:
            return err

        # validate action via serializer
        serializer = FarmerApproveSerializer(data={"action": action})
        if not serializer.is_valid():
            return Response(
                {"error": f"Invalid action '{action}'. Use 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        farmer = get_object_or_404(User, id=user_id, role="farmer")

        if action == "approve":
            if farmer.is_verified:
                return Response(
                    {"error": "Farmer is already approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            farmer.is_verified = True
            farmer.save(update_fields=["is_verified"])

            seller = getattr(farmer, "seller", None)
            if seller:
                seller.is_verified = True
                seller.save(update_fields=["is_verified"])

            return Response({
                "message":  "Farmer approved successfully.",
                "data":     FarmerListSerializer(farmer).data,
            })

        elif action == "reject":
            farmer.delete()
            return Response({
                "message": "Farmer rejected and account removed.",
            }, status=status.HTTP_200_OK)

        elif action == "revoke":
            if not farmer.is_verified:
                return Response(
                    {"error": "Farmer is not approved yet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            farmer.is_verified = False
            farmer.save(update_fields=["is_verified"])

            seller = getattr(farmer, "seller", None)
            if seller:
                seller.is_verified = False
                seller.save(update_fields=["is_verified"])

            return Response({
                "message": "Farmer approval revoked.",
                "data":    FarmerListSerializer(farmer).data,
            })


# ══════════════════════════════════════════════════════════
# VENDOR MANAGEMENT
# ══════════════════════════════════════════════════════════

class AdminPendingVendorsView(APIView):
    """GET  /api/admin/vendors/pending/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        vendors = User.objects.filter(
            role="vendor",
            is_verified=False,
        ).select_related("seller").order_by("-created_at")

        serializer = VendorListSerializer(vendors, many=True)
        return Response({
            "count":   vendors.count(),
            "results": serializer.data,
        })


class AdminAllVendorsView(APIView):
    """GET  /api/admin/vendors/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        vendors = User.objects.filter(
            role="vendor",
            is_verified=True,
        ).select_related("seller").order_by("-created_at")

        serializer = VendorListSerializer(vendors, many=True)
        return Response({
            "count":   vendors.count(),
            "results": serializer.data,
        })


class AdminApproveVendorView(APIView):
    """
    POST /api/admin/vendors/<user_id>/approve/
    POST /api/admin/vendors/<user_id>/reject/
    POST /api/admin/vendors/<user_id>/revoke/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id, action):
        err = is_admin(request)
        if err:
            return err

        if action not in ("approve", "reject", "revoke"):
            return Response(
                {"error": f"Invalid action '{action}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vendor = get_object_or_404(User, id=user_id, role="vendor")

        if action == "approve":
            if vendor.is_verified:
                return Response(
                    {"error": "Vendor is already approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            vendor.is_verified = True
            vendor.save(update_fields=["is_verified"])

            seller = getattr(vendor, "seller", None)
            if seller:
                seller.is_verified = True
                seller.save(update_fields=["is_verified"])

            return Response({
                "message": "Vendor approved successfully.",
                "data":    VendorListSerializer(vendor).data,
            })

        elif action == "reject":
            vendor.delete()
            return Response({"message": "Vendor rejected and account removed."})

        elif action == "revoke":
            if not vendor.is_verified:
                return Response(
                    {"error": "Vendor is not approved yet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            vendor.is_verified = False
            vendor.save(update_fields=["is_verified"])

            seller = getattr(vendor, "seller", None)
            if seller:
                seller.is_verified = False
                seller.save(update_fields=["is_verified"])

            return Response({
                "message": "Vendor approval revoked.",
                "data":    VendorListSerializer(vendor).data,
            })


# ══════════════════════════════════════════════════════════
# COLLECTION CENTER MANAGEMENT
# ══════════════════════════════════════════════════════════

class AdminCollectionCenterListView(APIView):
    """
    GET   /api/admin/collection-centers/
    POST  /api/admin/collection-centers/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        centers = CollectionCenter.objects.select_related("user").order_by("-created_at")
        serializer = CollectionCenterSerializer(centers, many=True)
        return Response({
            "count":   centers.count(),
            "results": serializer.data,
        })

    def post(self, request):
        err = is_admin(request)
        if err:
            return err

        # user_id must be passed — the CC must be linked to a user with role=collection_center
        user_id = request.data.get("user_id")
        user = get_object_or_404(User, id=user_id, role="collection_center")

        if hasattr(user, "collectioncenter"):
            return Response(
                {"error": "This user already has a collection center."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CollectionCenterCreateSerializer(data=request.data)
        if serializer.is_valid():
            center = serializer.save(user=user, is_verified=True)
            return Response(
                {
                    "message": "Collection center created.",
                    "data":    CollectionCenterSerializer(center).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCollectionCenterDetailView(APIView):
    """
    GET    /api/admin/collection-centers/<pk>/
    PATCH  /api/admin/collection-centers/<pk>/
    DELETE /api/admin/collection-centers/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        center = get_object_or_404(CollectionCenter, id=pk)
        serializer = CollectionCenterSerializer(center)
        return Response(serializer.data)

    def patch(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        center = get_object_or_404(CollectionCenter, id=pk)
        serializer = CollectionCenterCreateSerializer(
            center, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Collection center updated.",
                "data":    CollectionCenterSerializer(center).data,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        center = get_object_or_404(CollectionCenter, id=pk)
        center.delete()
        return Response(
            {"message": "Collection center deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )


# ══════════════════════════════════════════════════════════
# ORDER MANAGEMENT
# ══════════════════════════════════════════════════════════

class AdminOrdersView(APIView):
    """GET  /api/admin/orders/?status=placed&flow_type=farmer"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        orders = Order.objects.select_related(
            "user", "collection_center", "address"
        ).prefetch_related(
            "orderitem_set__variant__product",
            "orderitem_set__seller",
        ).order_by("-created_at")

        order_status = request.query_params.get("status")
        flow_type    = request.query_params.get("flow_type")
        if order_status:
            orders = orders.filter(status=order_status)
        if flow_type:
            orders = orders.filter(flow_type=flow_type)

        serializer = AdminOrderSerializer(orders, many=True)
        return Response({
            "count":   orders.count(),
            "results": serializer.data,
        })


class AdminOrderDetailView(APIView):
    """GET  /api/admin/orders/<pk>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        order = get_object_or_404(
            Order.objects.select_related(
                "user", "collection_center", "address"
            ).prefetch_related(
                "orderitem_set__variant__product",
                "orderitem_set__seller",
                "status_history",
            ),
            id=pk,
        )
        serializer = AdminOrderSerializer(order)
        return Response(serializer.data)


# ══════════════════════════════════════════════════════════
# USER MANAGEMENT
# ══════════════════════════════════════════════════════════

class AdminUserListView(APIView):
    """GET  /api/admin/users/?role=user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = is_admin(request)
        if err:
            return err

        users = User.objects.order_by("-created_at")

        role = request.query_params.get("role")
        if role:
            users = users.filter(role=role)

        serializer = AdminUserListSerializer(users, many=True)
        return Response({
            "count":   users.count(),
            "results": serializer.data,
        })


class AdminUserDetailView(APIView):
    """
    GET    /api/admin/users/<pk>/
    PATCH  /api/admin/users/<pk>/
    DELETE /api/admin/users/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        user = get_object_or_404(User, id=pk)
        serializer = AdminUserListSerializer(user)
        return Response(serializer.data)

    def patch(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        user = get_object_or_404(User, id=pk)
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "User updated successfully.",
                "data":    AdminUserListSerializer(user).data,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        err = is_admin(request)
        if err:
            return err

        user = get_object_or_404(User, id=pk)
        if user.role == "admin":
            return Response(
                {"error": "Cannot delete another admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.delete()
        return Response(
            {"message": "User deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )