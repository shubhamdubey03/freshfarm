from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count

from core_app.models import Seller
from core_app.farmer.permissions import IsFarmer
from core_app.farmer.serializers import (
    FarmerProfileSerializer,
    FarmerProfileUpdateSerializer,
    ProductListSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    FarmerOrderItemSerializer,
    FarmerOrderDetailSerializer,
    FarmerBatchListSerializer,
    FarmerBatchDetailSerializer,
    FarmerSalarySerializer,
)
from core_product.models import Product
from core_order.models import (
    FarmerOrder,
    FarmerOrderBatch,
    FarmerSalary,
    OrderStatusHistory,
)

# ──────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────


def get_farmer_seller(user):
    return get_object_or_404(Seller, user=user, seller_type="farmer")


# ──────────────────────────────────────────
# 1. PROFILE — GET
# ──────────────────────────────────────────


class FarmerProfileView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request):
        seller = get_farmer_seller(request.user)
        serializer = FarmerProfileSerializer(seller, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        seller = get_farmer_seller(request.user)
        serializer = FarmerProfileUpdateSerializer(
            seller, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Profile updated.",
                    **serializer.data,
                }
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────
# 2. PRODUCTS — LIST
# ──────────────────────────────────────────


class FarmerProductListView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request):
        seller = get_farmer_seller(request.user)

        products = (
            Product.objects.filter(seller=seller)
            .prefetch_related("variants", "category")
            .order_by("-created_at")
        )

        serializer = ProductListSerializer(
            products, context={"request": request}, many=True
        )

        return Response(
            {
                "count": products.count(),
                "results": serializer.data,
            }
        )

    def post(self, request):
        seller = get_farmer_seller(request.user)

        serializer = ProductCreateSerializer(data=request.data)

        if serializer.is_valid():
            product = serializer.save(seller=seller)
            return Response(
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category.name,
                    "note": "Price will be set by admin.",
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────
# 3. PRODUCTS — UPDATE / DELETE
# ──────────────────────────────────────────


class FarmerProductDetailView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def patch(self, request, pk):
        seller = get_farmer_seller(request.user)
        product = get_object_or_404(Product, id=pk, seller=seller)

        serializer = ProductUpdateSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # return updated variant info
            variant = product.variants.first()
            return Response(
                {
                    "id": product.id,
                    "name": product.name,
                    "stock": variant.stock if variant else None,
                    "harvest_date": variant.harvest_date if variant else None,
                }
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        seller = get_farmer_seller(request.user)
        product = get_object_or_404(Product, id=pk, farmer=seller)
        product.delete()
        return Response(
            {"message": "Product removed."}, status=status.HTTP_204_NO_CONTENT
        )


# ──────────────────────────────────────────
# 4. MY ASSIGNED ORDERS — LIST
# ──────────────────────────────────────────


class FarmerOrderListView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request):
        seller = get_farmer_seller(request.user)

        farmer_orders = (
            FarmerOrder.objects.filter(farmer=seller)
            .select_related(
                "order_item__variant__product",
                "batch",
            )
            .order_by("-batch__date")
        )

        serializer = FarmerOrderItemSerializer(
            farmer_orders, many=True, context={"request": request}
        )
        return Response(
            {
                "count": farmer_orders.count(),
                "results": serializer.data,
            }
        )


# ──────────────────────────────────────────
# 5. MY ASSIGNED ORDERS — DETAIL
# ──────────────────────────────────────────


class FarmerOrderDetailView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request, pk):
        seller = get_farmer_seller(request.user)
        farmer_order = get_object_or_404(FarmerOrder, id=pk, farmer=seller)
        serializer = FarmerOrderDetailSerializer(farmer_order)
        return Response(serializer.data)


# ──────────────────────────────────────────
# 5b. MARK ORDER READY — sent to collection
# ──────────────────────────────────────────


class FarmerOrderReadyView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def post(self, request, pk):
        seller = get_farmer_seller(request.user)
        farmer_order = get_object_or_404(FarmerOrder, id=pk, farmer=seller)
        order = farmer_order.order_item.order

        # mark order as sent to collection
        order.status = "sent_to_collection"
        order.save(update_fields=["status"])

        # log history
        OrderStatusHistory.objects.create(
            order=order,
            status="sent_to_collection",
            updated_by=request.user,
        )

        # update or create collection order
        from core_app.models import CollectionOrder

        collection_order, created = CollectionOrder.objects.update_or_create(
            order=order,
            collection_center=order.collection_center,
            defaults={"status": "pending"},
        )

        # Notify Collection Center
        if order.collection_center and order.collection_center.user:
            from core_app.utils.fcm import send_notification

            send_notification(
                user=order.collection_center.user,
                title="📦 New Dispatch from Farmer",
                body=f"Farmer {seller.farm_name} has dispatched order #{order.id} to your center.",
                data={"order_id": order.id, "status": "pending"},
            )

        # Notify Buyer
        try:
            from core_app.utils.fcm import send_notification
            send_notification(
                user=order.user,
                title="🌾 Produce Dispatched by Farmer",
                body=f"Farmer {seller.farm_name} has dispatched the produce for your order #{order.id} to the collection center.",
                data={"order_id": str(order.id), "status": "sent_to_collection"}
            )
        except Exception as e:
            print("Failed to notify buyer on farmer dispatch:", e)

        return Response(
            {
                "message": "Order marked ready and dispatched to collection center.",
                "farmer_order_id": farmer_order.id,
                "order_status": order.status,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────
# 6. MY BATCHES — LIST
# ──────────────────────────────────────────


class FarmerBatchListView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request):
        seller = get_farmer_seller(request.user)

        # get batches where this farmer has orders
        batch_ids = (
            FarmerOrder.objects.filter(farmer=seller)
            .values_list("batch_id", flat=True)
            .distinct()
        )

        batches = (
            FarmerOrderBatch.objects.filter(id__in=batch_ids)
            .annotate(
                total_items=Count("farmerorder"),
                total_quantity=Sum("farmerorder__quantity"),
            )
            .order_by("-date")
        )
        serializer = FarmerBatchListSerializer(batches, many=True)
        return Response(
            {
                "count": batches.count(),
                "results": serializer.data,
            }
        )


# ──────────────────────────────────────────
# 7. MY BATCHES — DETAIL
# ──────────────────────────────────────────


class FarmerBatchDetailView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request, pk):
        seller = get_farmer_seller(request.user)

        batch = get_object_or_404(FarmerOrderBatch, id=pk)

        # verify this farmer has orders in this batch
        has_orders = FarmerOrder.objects.filter(batch=batch, farmer=seller).exists()

        if not has_orders:
            return Response(
                {"error": "You have no orders in this batch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = FarmerBatchDetailSerializer(batch, context={"farmer": seller})
        return Response(serializer.data)


# ──────────────────────────────────────────
# 8. CONFIRM DISPATCH TO COLLECTION CENTER
# ──────────────────────────────────────────


class FarmerBatchConfirmDispatchView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def post(self, request, pk):
        seller = get_farmer_seller(request.user)
        batch = get_object_or_404(FarmerOrderBatch, id=pk)

        # verify farmer belongs to this batch
        farmer_orders = FarmerOrder.objects.filter(batch=batch, farmer=seller)
        if not farmer_orders.exists():
            return Response(
                {"error": "You have no orders in this batch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not batch.is_closed:
            return Response(
                {"error": "Batch is not closed yet. Wait until 6 PM cutoff."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # update all related CollectionOrders to pending
        from core_app.models import CollectionOrder

        for farmer_order in farmer_orders:
            order = farmer_order.order_item.order

            # mark order as sent to collection
            if order.status == "farmer_assigned":
                order.status = "sent_to_collection"
                order.save(update_fields=["status"])

            # update or create collection order
            CollectionOrder.objects.update_or_create(
                order=order,
                collection_center=order.collection_center,
                defaults={"status": "pending"},
            )

        dispatched_at = timezone.now()

        return Response(
            {
                "message": "Dispatch confirmed. Collection center notified.",
                "batch_id": batch.id,
                "total_orders_dispatched": farmer_orders.count(),
                "dispatched_at": dispatched_at,
            }
        )


# ──────────────────────────────────────────
# 9. SALARY HISTORY
# ──────────────────────────────────────────


class FarmerSalaryView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def get(self, request):
        seller = get_farmer_seller(request.user)

        salaries = FarmerSalary.objects.filter(farmer=seller).order_by("-month")

        serializer = FarmerSalarySerializer(salaries, many=True)
        return Response(
            {
                "count": salaries.count(),
                "results": serializer.data,
            }
        )
