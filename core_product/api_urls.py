from django.urls import path
from core_product.api_views import *
from core_product.vendor_views import *

urlpatterns = [
    path("products/", ProductListAPIView.as_view()),
    path("product-detail/", ProductDetailAPIView.as_view()),
    path("categories/", CategoryListAPIView.as_view()),
    path('cart/add/', AddToCartAPIView.as_view()),
    path('cart/', GetCartAPIView.as_view()),
    path('cart/update/', UpdateCartAPIView.as_view()),
    path('cart/remove/', RemoveCartAPIView.as_view()),
    path('create/', create_product),
    path('', get_products),
    path('<int:pk>/', get_product),
    path('update/<int:pk>/', update_product),
    path('delete/<int:pk>/', delete_product),

]