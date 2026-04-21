from django.urls import path
from .delivery_views import *

urlpatterns = [
    path("orders/", DeliveryOrderListAPI.as_view()),
    path("pickup/<int:order_id>/", PickupOrderAPI.as_view()),
    path("deliver/<int:order_id>/", DeliverOrderAPI.as_view()),
    path("location/<int:order_id>/", UpdateDeliveryLocationAPI.as_view()),
]