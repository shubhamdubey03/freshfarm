from django.urls import path
from core_app.api_views import (
    # auth
    RegisterView,
    SendOTPView,
    VerifyOTPLoginView,
    GoogleLoginView,
    TokenRefreshAPIView,
    LogoutAPIView,

    # profile
    GetProfileAPIView,
    UpdateProfileAPIView,
    DeleteProfileAPIView,

    # address
    AddressListView,
    AddressDetailView,
    geocode_address,
    reverse_geocode,
    save_address,
    get_user_addresses,

    # product & category
    CategoryListView,
    ProductListView,
    ProductDetailView,
    ProductVariantListView,
    ProductVariantDetailView,
    ProductVariantCreateView,      # ← new
    ProductVariantManageView,

    # cart
    CartListView,
    CartItemDetailView,

    # order
    CreateOrderAPIView,
    GetOrdersAPIView,
    OrderDetailAPIView,
    CancelOrderAPIView,

    # payment
    InitiatePaymentView,
    VerifyPaymentView,

    # subscription
    SubscriptionListView,
    CancelSubscriptionView,
)

urlpatterns = [

    # ── auth ──────────────────────────────
    path("auth/register/", RegisterView.as_view(),       name="register"),
    path("auth/send-otp/", SendOTPView.as_view(),         name="send-otp"),
    path("auth/verify-otp/", VerifyOTPLoginView.as_view(),  name="verify-otp"),
    path("auth/google/",GoogleLoginView.as_view(),     name="google-login"),
    path("auth/token/refresh/", TokenRefreshAPIView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutAPIView.as_view(),       name="logout"),

    # ── profile ───────────────────────────
    path("user/profile/", GetProfileAPIView.as_view(),    name="get-profile"),
    path("user/profile/update/",UpdateProfileAPIView.as_view(), name="update-profile"),
    path("user/profile/delete/<int:user_id>/",DeleteProfileAPIView.as_view(), name="delete-profile"),

    # ── address ───────────────────────────
    path("user/addresses/", AddressListView.as_view(),   name="address-list"),
    path("user/addresses/<int:pk>/",AddressDetailView.as_view(),name="address-detail"),
    path("address/geocode/", geocode_address,name="geocode address"),
    path("address/reverse-geocode/", reverse_geocode,name="reverse geocode"),
    path("address/save/", save_address,name="save address"),
    path("address/list/", get_user_addresses,name="user address"),

    # ── products ──────────────────────────
    path("user/categories/", CategoryListView.as_view(),  name="category-list"),
    path("user/products/", ProductListView.as_view(),   name="product-list"),
    path("user/products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),

    # ── variants ──────────────────────────
    path(
        "user/products/<int:product_pk>/variants/",
        ProductVariantListView.as_view(),
        name="variant-list"
    ),
    path(
        "user/products/<int:product_pk>/variants/create/",
        ProductVariantCreateView.as_view(),        # ← new
        name="variant-create"
    ),
    path(
        "user/products/<int:product_pk>/variants/<int:variant_pk>/",
        ProductVariantDetailView.as_view(),
        name="variant-detail"
    ),
    path(
        "user/products/<int:product_pk>/variants/<int:variant_pk>/manage/",
        ProductVariantManageView.as_view(),         # ← new
        name="variant-manage"
    ),
    # ── cart ──────────────────────────────
    path("user/cart/",  CartListView.as_view(), name="cart-list"),
    path("user/cart/<int:pk>/", CartItemDetailView.as_view(),name="cart-detail"),

    # ── orders ────────────────────────────
    path("user/orders/", CreateOrderAPIView.as_view(), name="create-order"),
    path("user/orders/list/", GetOrdersAPIView.as_view(),   name="order-list"),
    path("user/orders/<int:pk>/", OrderDetailAPIView.as_view(), name="order-detail"),
    path("user/orders/<int:pk>/cancel/", CancelOrderAPIView.as_view(), name="order-cancel"),

    # ── payments ──────────────────────────
    path("user/payments/initiate/", InitiatePaymentView.as_view(),  name="payment-initiate"),
    path("user/payments/verify/", VerifyPaymentView.as_view(),   name="payment-webhook"),

    # ── subscriptions ─────────────────────
    path("user/subscriptions/", SubscriptionListView.as_view(),   name="subscription-list"),
    path("user/subscriptions/<int:pk>/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
]