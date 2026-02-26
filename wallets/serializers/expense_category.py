from rest_framework import serializers

from wallets.models import ExpenseCategory


class ExpenseCategoryReadSerializer(serializers.ModelSerializer):
    user = serializers.UUIDField(read_only=True, source='user_id', help_text='Category owner user ID.')

    class Meta:
        model = ExpenseCategory
        fields = (
            'id',
            'user',
            'name',
            'icon',
            'color',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ExpenseCategoryCreateUpdateSerializer(serializers.ModelSerializer):
    user = serializers.UUIDField(read_only=True, source='user_id', help_text='Category owner user ID.')
    name = serializers.CharField(
        max_length=60,
        required=True,
        help_text='Category name. Must be unique per user.',
        error_messages={
            'blank': 'Category name is required.',
            'required': 'Category name is required.',
        },
    )
    icon = serializers.CharField(
        max_length=80,
        required=True,
        allow_blank=False,
        help_text='Category icon identifier (for example: mdi:food).',
        error_messages={
            'blank': 'Icon is required.',
            'required': 'Icon is required.',
        },
    )
    color = serializers.CharField(
        max_length=32,
        required=True,
        allow_blank=False,
        help_text='Category color (for example: #FF6B00).',
        error_messages={
            'blank': 'Color is required.',
            'required': 'Color is required.',
        },
    )

    class Meta:
        model = ExpenseCategory
        fields = (
            'id',
            'user',
            'name',
            'icon',
            'color',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def validate_name(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError('Category name is required.')

        request = self.context.get('request')
        user = request.user if request else None
        if user:
            # Case-insensitive uniqueness enforced at serializer level for cross-DB compatibility.
            qs = ExpenseCategory.objects.filter(user=user, name__iexact=normalized)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('You already have a category with this name.')

        return normalized
