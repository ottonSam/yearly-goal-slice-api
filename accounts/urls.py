from django.urls import path
from .views import MeView, RefreshTokenView, RegisterView, LoginView


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
]
