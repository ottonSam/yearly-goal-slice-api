from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, response, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import PasswordChangeSerializer, UserProfileUpdateSerializer, UserSerializer


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


class ProfileUpdateView(generics.UpdateAPIView):
    """
    Update basic user data (first name, last name, email) for the authenticated user.
    """

    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['put', 'patch']

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """
    Change password for the authenticated user after validating the current password.
    """

    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            raise ValidationError({"current_password": "Current password is incorrect."})

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return response.Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)
