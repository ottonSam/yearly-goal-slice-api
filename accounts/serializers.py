from django.contrib.auth import get_user_model, password_validation
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .email_verification import refresh_and_send_verification_code


User = get_user_model()


class NameValidationMixin:
    def validate_first_name(self, value):
        return self._validate_name(value, field='first_name')

    def validate_last_name(self, value):
        return self._validate_name(value, field='last_name')

    def _validate_name(self, value, field: str):
        if len(value) < 3:
            raise serializers.ValidationError("Must be at least 3 characters.")
        if any(char.isdigit() for char in value):
            raise serializers.ValidationError("Numbers are not allowed.")
        return value


class UserSerializer(NameValidationMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name')
        read_only_fields = ('id',)
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate_password(self, value):
        password_validation.validate_password(value, self.instance)
        return value


class UserProfileUpdateSerializer(NameValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'username')
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
        }


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True, allow_blank=False)
    new_password = serializers.CharField(write_only=True, required=True, allow_blank=False)

    def validate_new_password(self, value):
        user = self.context.get('request').user if self.context.get('request') else None
        password_validation.validate_password(value, user)
        return value

    def validate(self, attrs):
        if attrs.get('current_password') == attrs.get('new_password'):
            raise serializers.ValidationError({"new_password": "New password must be different from the current one."})
        return attrs


class EmailVerificationTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if not user.email_verified:
            now = timezone.now()
            if user.email_verification_expires_at and user.email_verification_expires_at <= now:
                refresh_and_send_verification_code(user)
                raise serializers.ValidationError(
                    {"detail": "Code expired. A new code was sent to your email."}
                )
            refresh_and_send_verification_code(user)
            raise serializers.ValidationError(
                {"detail": "User not confirmed. A code was sent to your email."}
            )
        return data


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, allow_blank=False, write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        code = attrs.get("code")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if user.email_verified:
            raise serializers.ValidationError({"detail": "Email already confirmed."})

        if user.is_email_verification_expired():
            refresh_and_send_verification_code(user)
            raise serializers.ValidationError(
                {"detail": "Code expired. A new code was sent to your email."}
            )

        if not user.check_email_verification_code(code):
            raise serializers.ValidationError({"code": "Invalid code."})

        attrs["user"] = user
        return attrs
