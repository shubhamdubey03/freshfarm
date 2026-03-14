from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .api_views import *


urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path("google-login/", GoogleLoginView.as_view()),
    path("refresh/", TokenRefreshView.as_view()),
]
    

