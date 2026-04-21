from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
import json
from .models import Product,ProductVariant
from .vendor_serializers import ProductSerializer,UpdateInventorySerializer,UpdateOrderStatusSerializer
from core_order.models import Order


# ✅ CREATE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product(request):

    data = request.data.dict()  # 🔥 VERY IMPORTANT

    variants = request.data.get("variants")

    if not variants:
        return Response({"error": "variants is required"}, status=400)

    try:
        variants = json.loads(variants)
    except:
        return Response({"error": "Invalid variants JSON"}, status=400)

    serializer = ProductSerializer(data=data)

    if serializer.is_valid():
        product = serializer.save(farmer=request.user.seller)

        # ✅ Create variants manually (BEST WAY)
        for variant in variants:
            ProductVariant.objects.create(
                product=product,
                **variant
            )

        return Response({
            "message": "Product created successfully"
        }, status=201)

    return Response(serializer.errors, status=400)


# ✅ GET ALL (only logged-in user's products)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_products(request):
    products = Product.objects.filter(farmer=request.user.seller)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


# ✅ GET SINGLE
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product(request, pk):
    try:
        product = Product.objects.get(id=pk)
    except Product.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    # 🔐 owner check
    if product.farmer != request.user.seller:
        raise PermissionDenied("You are not allowed to view this product")

    serializer = ProductSerializer(product)
    return Response(serializer.data)


# ✅ UPDATE
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_product(request, pk):
    try:
        product = Product.objects.get(id=pk)
    except Product.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    # 🔐 owner check
    if product.farmer != request.user.seller:
        raise PermissionDenied("You are not allowed to update this product")

    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors)


# ✅ DELETE
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    try:
        product = Product.objects.get(id=pk)
    except Product.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    # 🔐 owner check
    if product.farmer != request.user.seller:
        raise PermissionDenied("You are not allowed to delete this product")

    product.delete()
    return Response({"message": "Deleted successfully"})


class UpdateInventoryAPI(APIView):

    def post(self, request):
        serializer = UpdateInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = serializer.save()

        return Response({
            "message": "Stock updated",
            "stock": variant.stock
        })


class UpdateOrderStatusAPI(APIView):

    def post(self, request, order_id):
        order = Order.objects.get(id=order_id)

        serializer = UpdateOrderStatusSerializer(
            data=request.data,
            context={"order": order, "request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Order status updated"})
