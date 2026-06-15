from django.urls import path
from core_app.delivery.views import (
    DeliveryAssignmentListView,
    DeliveryAssignmentDetailView,
    DeliveryPickedUpView,
    DeliveryDeliveredView,
    DeliveryReturnedView,
    DeliveryHistoryView,
    DeliveryEarningsView,
    DeliveryLocationUpdateView,
    DeliveryProfileView,
    DeliveryAcceptView,
    DeliveryDeclineView,
    DeliveryFCMTokenView,
)

urlpatterns = [
    # profile
    path("profile/", DeliveryProfileView.as_view(), name="delivery-profile"),
    # FCM Token
    path("fcm-token/", DeliveryFCMTokenView.as_view(), name="delivery-fcm-token"),
    # assignments
    path(
        "assignments/",
        DeliveryAssignmentListView.as_view(),
        name="delivery-assignments",
    ),
    path(
        "assignments/<int:pk>/",
        DeliveryAssignmentDetailView.as_view(),
        name="delivery-assignment-detail",
    ),
    path(
        "assignments/<int:pk>/accept/",
        DeliveryAcceptView.as_view(),
        name="delivery-accept",
    ),
    path(
        "assignments/<int:pk>/decline/",
        DeliveryDeclineView.as_view(),
        name="delivery-decline",
    ),
    path(
        "assignments/<int:pk>/picked-up/",
        DeliveryPickedUpView.as_view(),
        name="delivery-picked-up",
    ),
    path(
        "assignments/<int:pk>/delivered/",
        DeliveryDeliveredView.as_view(),
        name="delivery-delivered",
    ),
    path(
        "assignments/<int:pk>/returned/",
        DeliveryReturnedView.as_view(),
        name="delivery-returned",
    ),
    # history & earnings
    path("history/", DeliveryHistoryView.as_view(), name="delivery-history"),
    path("earnings/", DeliveryEarningsView.as_view(), name="delivery-earnings"),
    # location
    path("location/", DeliveryLocationUpdateView.as_view(), name="delivery-location"),
]
