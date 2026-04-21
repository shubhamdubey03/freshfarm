from django.urls import path
from .api_views import *
from .delivery_views import *

urlpatterns = [
    path("create/", CreateOrderAPIView.as_view()),
    path("", GetOrdersAPIView.as_view()),
    path("details/<int:pk>/", OrderDetailAPIView.as_view()),
    path("delivery/orders/", DeliveryOrderListAPI.as_view()),
    path("delivery/pickup/<int:order_id>/", PickupOrderAPI.as_view()),
    path("delivery/deliver/<int:order_id>/", DeliverOrderAPI.as_view()),
    path("delivery/location/<int:order_id>/", UpdateDeliveryLocationAPI.as_view()),
]