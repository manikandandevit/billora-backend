from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenVerifyView

from .views import HealthView, LoginView, MeView, ThrottledTokenRefreshView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("auth/logout/", TokenBlacklistView.as_view(), name="token-logout"),
    path("me/", MeView.as_view(), name="me"),
]
