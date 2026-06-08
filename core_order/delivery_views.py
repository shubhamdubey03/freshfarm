from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from core_order.models import Delivery, OrderStatusHistory,SellerEarning, DeliveryEarning, AdminEarning
from .serializers import OrderSerializer
from core_order.constants import OrderStatus, DeliveryStatus


class DeliveryOrderListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        deliveries = Delivery.objects.filter(
            delivery_boy=user
        ).select_related("order").prefetch_related(
            "order__orderitem_set__variant__product"
        )

        orders = [d.order for d in deliveries]

        serializer = OrderSerializer(orders, many=True).data

        return Response({
            "success": True,
            "count": len(orders),
            "data": serializer.data
        })  
    
class PickupOrderAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        try:
            delivery = Delivery.objects.get(order_id=order_id, delivery_boy=request.user)
        except Delivery.DoesNotExist:
            return Response({"error": "Delivery not found"}, status=404)

        if delivery.status != DeliveryStatus.ASSIGNED:
            return Response({"error": "invalid state"}, status=400)

        delivery.status =DeliveryStatus.PICKED
        delivery.pickup_time = timezone.now()
        delivery.save()

        order = delivery.order

        # ✅ Update Order status
        if order.flow_type == "vendor":
            order.status =  OrderStatus.OUT_FOR_DELIVERY
        else:
            order.status = OrderStatus.OUT_FOR_DELIVERY
        order.save()

        # ✅ History
        OrderStatusHistory.objects.create(
            order=order,
            status=OrderStatus.OUT_FOR_DELIVERY,
            updated_by=request.user
        )

        return Response({"message": "Order picked successfully"})

class DeliverOrderAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        otp = request.data.get("otp")

        try:
            delivery = Delivery.objects.get(order_id=order_id, delivery_boy=request.user)
        except Delivery.DoesNotExist:
            return Response({"error": "Delivery not found"}, status=404)
        
        if delivery.status != DeliveryStatus.PICKED:
            return Response({"error": "Order not picked yet"}, status=400)


        if delivery.otp != otp:
            return Response({"error": "Invalid OTP"}, status=400)

        delivery.status != DeliveryStatus.DELIVERED
        delivery.delivery_time = timezone.now()
        delivery.save()

        order = delivery.order
        order.status = OrderStatus.DELIVERED

        # ✅ COD payment update
        if order.order_type == "cod":
            order.payment_status = "paid"

        order.save()

        # ✅ History
        OrderStatusHistory.objects.create(
            order=order,
            status=OrderStatus.DELIVERED,
            updated_by=request.user
        )

        # 🔥 CREATE EARNINGS (80% Admin, 10% Delivery, 10% Vendor)
        import decimal
        
        # 1. Admin Earning (80% of total order)
        admin_amount = order.total_price * decimal.Decimal("0.80")
        AdminEarning.objects.get_or_create(
            order=order,
            defaults={"amount": admin_amount}
        )
        
        # 2. Delivery Earning (10% of total order)
        delivery_amount = order.total_price * decimal.Decimal("0.10")
        DeliveryEarning.objects.get_or_create(
            delivery_boy=request.user,
            order=order,
            defaults={"amount": delivery_amount}
        )

        # 3. Vendor Earning (10% of item total for each item)
        for item in order.orderitem_set.all():
            if item.seller:
                vendor_amount = (item.price * item.quantity) * decimal.Decimal("0.10")
                SellerEarning.objects.get_or_create(
                    seller=item.seller,
                    order=order,
                    order_item=item,
                    defaults={"amount": vendor_amount}
                )

        return Response({"message": "Order delivered successfully"})
class UpdateDeliveryLocationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        lat = request.data.get("latitude")
        lng = request.data.get("longitude")

        if not lat or not lng:
            return Response({"error": "Latitude and Longitude required"}, status=400)

        try:
            delivery = Delivery.objects.get(order_id=order_id, delivery_boy=request.user)
        except Delivery.DoesNotExist:
            return Response({"error": "Delivery not found"}, status=404)
        
        if delivery.status == DeliveryStatus.ASSIGNED:
            return Response({"error": "Pickup not done yet"}, status=400)


        delivery.latitude = lat
        delivery.longitude = lng
        delivery.save()

        return Response({
            "message": "Location updated",
            "location": {
                "latitude": lat,
                "longitude": lng
            }
        })     