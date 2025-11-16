from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import UserSerializer


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Allows a new user to sign up with username, email and password.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    """
    Returns data for the currently authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return response.Response(serializer.data)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]


class RefreshTokenView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
