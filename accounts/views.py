from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, response, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .email_verification import refresh_and_send_verification_code
from .serializers import (
    EmailVerificationTokenObtainPairSerializer,
    PasswordChangeSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Allows a new user to sign up with username, email and password.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save(email_verified=False)
        refresh_and_send_verification_code(user)


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
    serializer_class = EmailVerificationTokenObtainPairSerializer


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


class VerifyEmailView(generics.GenericAPIView):
    """
    Verify a user's email using a confirmation code.
    """

    serializer_class = VerifyEmailSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.email_verified = True
        user.email_verification_code_hash = None
        user.email_verification_expires_at = None
        user.save(update_fields=["email_verified", "email_verification_code_hash", "email_verification_expires_at"])
        return response.Response({"detail": "Email confirmed successfully."}, status=status.HTTP_200_OK)
