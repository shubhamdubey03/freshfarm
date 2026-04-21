from django.urls import path
from core_app.collection_center.views import (
    CollectionCenterProfileView,
    CollectionOrderListView,
    CollectionOrderDetailView,
    CollectionOrderReceivedView,
    CollectionOrderReadyView,
    CollectionDeliveryListView,
    CollectionDeliveryVerifyOTPView,
)

urlpatterns = [

    # profile
    path(
        "profile/",
        CollectionCenterProfileView.as_view(),
        name="collection-profile"
    ),
    # orders
    path(
        "orders/",
        CollectionOrderListView.as_view(),
        name="collection-orders"
    ),
    path(
        "orders/<int:pk>/",
        CollectionOrderDetailView.as_view(),
        name="collection-order-detail"
    ),
    path(
        "orders/<int:pk>/received/",
        CollectionOrderReceivedView.as_view(),
        name="collection-order-received"
    ),
    path(
        "orders/<int:pk>/ready/",
        CollectionOrderReadyView.as_view(),
        name="collection-order-ready"
    ),

    # deliveries
    path(
        "deliveries/",
        CollectionDeliveryListView.as_view(),
        name="collection-deliveries"
    ),
    path(
        "deliveries/<int:pk>/verify-otp/",
        CollectionDeliveryVerifyOTPView.as_view(),
        name="collection-delivery-verify-otp"
    ),
]