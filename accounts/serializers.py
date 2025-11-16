from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
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
