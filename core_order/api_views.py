from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import F
from django.db import transaction
from core_product.models import CartItem
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import *
from core_app.models import CollectionCenter ,User
from django.shortcuts import get_object_or_404
from core_order.utility import verify_otp,send_otp



class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address_id = request.data.get("address")
        order_type = request.data.get("order_type", "pre_order")
        flow_type = request.data.get("flow_type", "farmer")  

        cart_items = CartItem.objects.select_related("variant__product").filter(user=user)

        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        total_price = 0
        center = CollectionCenter.objects.first()

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                address_id=address_id,
                collection_center=center,
                status="placed",
                total_price=0,
                order_type=order_type,  
                payment_status="pending",
                flow_type="flow_type"
            )

            OrderStatusHistory.objects.create(
                order=order,
                status="placed",
                updated_by=user
            )

            for item in cart_items:
                variant = item.variant

                if variant.stock < item.quantity:
                    return Response({
                        "error": f"Insufficient stock for {variant.product.name}"
                    }, status=400)

                # ✅ reduce stock
                variant.stock = F("stock") - item.quantity
                variant.save()
                variant.refresh_from_db()

                price = variant.price
                total_price += price * item.quantity

                # ✅ assign seller
                seller = variant.product.farmer

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    seller=seller,   
                    price=price,
                    quantity=item.quantity
                )

            # ✅ payment logic
            if order_type == "paid":
                order.payment_status = "paid"
             # 🔥 STATUS FLOW FIX
            if flow_type == "vendor":
                order.status = "out_for_delivery"
            else:
                order.status = "farmer_assigned"

            order.total_price = total_price
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status="at_collection_center",
                updated_by=None
            )

            cart_items.delete()

        return Response({
            "message": "Order created successfully",
            "data": OrderSerializer(order).data
        })  
class GetOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related(
            "orderitem_set__variant__product",
            "status_history"
        ).order_by("-id") 

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    

class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request,pk):
        
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
        
        return Response({"message": "Order ready. Delivery boy assigned automatically."})


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
