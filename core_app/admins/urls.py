# core_app/admin_urls.py

from django.urls import path
from core_app.admins.admin_views import (
    AdminDashboardView,
    AdminPendingFarmersView,
    AdminAllFarmersView,
    AdminApproveFarmerView,
    AdminPendingVendorsView,
    AdminAllVendorsView,
    AdminApproveVendorView,
    AdminCollectionCenterListView,
    AdminCollectionCenterDetailView,
    AdminOrdersView,
    AdminOrderDetailView,
    AdminUserListView,
    AdminUserDetailView,
)

urlpatterns = [
    # Dashboard
    path("dashboard/", AdminDashboardView.as_view()),

    # Farmers
    path("farmers/", AdminAllFarmersView.as_view()),
    path("farmers/pending/", AdminPendingFarmersView.as_view()),
    path("farmers/<int:user_id>/<str:action>/",AdminApproveFarmerView.as_view()),

    # Vendors
    path("vendors/", AdminAllVendorsView.as_view()),
    path("vendors/pending/", AdminPendingVendorsView.as_view()),
    path("vendors/<int:user_id>/<str:action>/",AdminApproveVendorView.as_view()),

    # Collection Centers
    path("collection-centers/", AdminCollectionCenterListView.as_view()),
    path("collection-centers/<int:pk>/", AdminCollectionCenterDetailView.as_view()),

    # Orders
    path("orders/", AdminOrdersView.as_view()),
    path("orders/<int:pk>/", AdminOrderDetailView.as_view()),

    # Users
    path("users/", AdminUserListView.as_view()),
    path("users/<int:pk>/", AdminUserDetailView.as_view()),
]