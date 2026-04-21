from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core_product.models import Product, Category, ProductVariant, CartItem
from core_product.serializers import ProductSerializer, CategorySerializer, CartItemSerializer


# ✅ PRODUCT LIST
class ProductListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = Product.objects.all().order_by("-id")
        serializer = ProductSerializer(products, many=True)

        return Response({
            "message": "Products fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# ✅ PRODUCT DETAIL
class ProductDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductSerializer(product)

        return Response({
            "message": "Product details fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# ✅ CATEGORY LIST
class CategoryListAPIView(APIView):

    def get(self, request):
        categories = Category.objects.all().order_by("name")
        serializer = CategorySerializer(categories, many=True)

        return Response({
            "message": "Categories fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# ✅ ADD TO CART
class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        variant_id = request.data.get("variant")
        quantity = int(request.data.get("quantity", 1))

        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=404)

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response({
            "message": "Item added to cart",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


# ✅ GET CART
class GetCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        serializer = CartItemSerializer(cart_items, many=True)

        return Response({
            "message": "Cart fetched successfully",
            "data": serializer.data
        })


# ✅ UPDATE CART
class UpdateCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            cart_item = CartItem.objects.get(id=pk, user=request.user)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=404)

        quantity = request.data.get("quantity")

        if not quantity:
            return Response({"error": "Quantity is required"}, status=400)

        cart_item.quantity = quantity
        cart_item.save()

        return Response({
            "message": "Cart updated successfully"
        })


# ✅ REMOVE FROM CART
class RemoveCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            cart_item = CartItem.objects.get(id=pk, user=request.user)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=404)

        cart_item.delete()

        return Response({
            "message": "Item removed from cart"
        }, status=200)