"""
URL configuration for freshapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from core_app.admin import freshapp_admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include

urlpatterns = [ 
    path('admin/', freshapp_admin.urls),
    path('api/',include('core_app.api_urls')),
    path("vendor/", include("core_app.vendor.urls")),
    path("farmer/", include("core_app.farmer.urls")), 
    path("collection/", include("core_app.collection_center.urls")),
    path("delivery/",   include("core_app.delivery.urls")), 
    path('api/product/',include('core_product.api_urls')),
    path('api/order/', include('core_order.api_urls')),
    path('api/delivery/',include('core_order.delivery_api_urls'))
]

if settings.DEBUG:
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
