from django.urls import path
from .views import (
    LoginView,
    MeView,
    PasswordChangeView,
    ProfileUpdateView,
    RefreshTokenView,
    RegisterView,
)


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/update-profile/', ProfileUpdateView.as_view(), name='auth-update-profile'),
    path('auth/change-password/', PasswordChangeView.as_view(), name='auth-change-password'),
]
