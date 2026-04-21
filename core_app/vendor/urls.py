from django.urls import path
from core_app.vendor.vendor_views import (
    VendorProfileView,
    VendorOrderListView,
    VendorOrderDetailView,
    VendorOrderAcceptView,
    VendorOrderPackedView,
    VendorOrderReadyView,
    VendorEarningsView,
    VendorEarningsSummaryView,
    VendorPayoutView,
)

urlpatterns = [
    # profile
    path("profile/<int:id>/", VendorProfileView.as_view(), name="vendor-profile"),

    # orders
    path("orders/", VendorOrderListView.as_view(), name="vendor-orders"),
    path("orders/<int:pk>/", VendorOrderDetailView.as_view(), name="vendor-order-detail"),
    path("orders/<int:pk>/accept/", VendorOrderAcceptView.as_view(), name="vendor-order-accept"),
    path("orders/<int:pk>/packed/", VendorOrderPackedView.as_view(), name="vendor-order-packed"),
    path("orders/<int:pk>/ready/", VendorOrderReadyView.as_view(), name="vendor-order-ready"),

    # earnings
    path("earnings/", VendorEarningsView.as_view(), name="vendor-earnings"),
    path("earnings/summary/", VendorEarningsSummaryView.as_view(), name="vendor-earnings-summary"),

    # payouts
    path("payouts/", VendorPayoutView.as_view(), name="vendor-payouts"),
]