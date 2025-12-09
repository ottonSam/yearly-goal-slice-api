from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers


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
