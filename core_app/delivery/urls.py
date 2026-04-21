from django.urls import path
from core_app.delivery.views import (
    DeliveryAssignmentListView,
    DeliveryAssignmentDetailView,
    DeliveryPickedUpView,
    DeliveryDeliveredView,
    DeliveryHistoryView,
    DeliveryEarningsView,
    DeliveryLocationUpdateView,
)

urlpatterns = [

    # assignments
    path(
        "assignments/",
        DeliveryAssignmentListView.as_view(),
        name="delivery-assignments"
    ),
    path(
        "assignments/<int:pk>/",
        DeliveryAssignmentDetailView.as_view(),
        name="delivery-assignment-detail"
    ),
    path(
        "assignments/<int:pk>/picked-up/",
        DeliveryPickedUpView.as_view(),
        name="delivery-picked-up"
    ),
    path(
        "assignments/<int:pk>/delivered/",
        DeliveryDeliveredView.as_view(),
        name="delivery-delivered"
    ),

    # history & earnings
    path(
        "history/",
        DeliveryHistoryView.as_view(),
        name="delivery-history"
    ),
    path(
        "earnings/",
        DeliveryEarningsView.as_view(),
        name="delivery-earnings"
    ),

    # location
    path(
        "location/",
        DeliveryLocationUpdateView.as_view(),
        name="delivery-location"
    ),
]