from django.urls import path
from core_app.farmer.views import (
    FarmerProfileView,
    FarmerProductListView,
    FarmerProductDetailView,
    FarmerOrderListView,
    FarmerOrderDetailView,
    FarmerBatchListView,
    FarmerBatchDetailView,
    FarmerBatchConfirmDispatchView,
    FarmerSalaryView,
)

urlpatterns = [

    # ── profile ──────────────────────────
    path(
        "profile/",
        FarmerProfileView.as_view(),
        name="farmer-profile"
    ),

    # ── products ─────────────────────────
    path(
        "products/",
        FarmerProductListView.as_view(),
        name="farmer-products"
    ),
    path(
        "products/<int:pk>/",
        FarmerProductDetailView.as_view(),
        name="farmer-product-detail"
    ),

    # ── orders ────────────────────────────
    path(
        "orders/",
        FarmerOrderListView.as_view(),
        name="farmer-orders"
    ),
    path(
        "orders/<int:pk>/",
        FarmerOrderDetailView.as_view(),
        name="farmer-order-detail"
    ),

    # ── batches ───────────────────────────
    path(
        "batches/",
        FarmerBatchListView.as_view(),
        name="farmer-batches"
    ),
    path(
        "batches/<int:pk>/",
        FarmerBatchDetailView.as_view(),
        name="farmer-batch-detail"
    ),
    path(
        "batches/<int:pk>/confirm-dispatch/",
        FarmerBatchConfirmDispatchView.as_view(),
        name="farmer-batch-confirm-dispatch"
    ),

    # ── salary ────────────────────────────
    path(
        "salary/",
        FarmerSalaryView.as_view(),
        name="farmer-salary"
    ),
]