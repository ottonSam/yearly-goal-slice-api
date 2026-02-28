from datetime import datetime

from rest_framework import serializers

from wallets.models import ExpenseCycle

from .expense import ExpenseReadSerializer


class ExpenseCycleReadSerializer(serializers.ModelSerializer):
    wallet = serializers.UUIDField(read_only=True, source='wallet_id', help_text='Related wallet ID.')

    class Meta:
        model = ExpenseCycle
        fields = (
            'id',
            'wallet',
            'month',
            'limit',
            'start_date',
            'end_date',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ExpenseCycleDetailSerializer(ExpenseCycleReadSerializer):
    expenses = ExpenseReadSerializer(many=True, read_only=True)

    class Meta(ExpenseCycleReadSerializer.Meta):
        fields = ExpenseCycleReadSerializer.Meta.fields + ('expenses',)
        read_only_fields = fields


class ExpenseCycleResolveSerializer(serializers.Serializer):
    wallet = serializers.UUIDField(required=True, help_text='Wallet ID.')
    date = serializers.DateField(
        required=False,
        help_text='Date to resolve cycle (YYYY-MM-DD).',
    )
    month = serializers.CharField(
        required=False,
        help_text='Cycle month in YYYY-MM or YYYY-MM-01.',
    )

    def validate_month(self, value):
        raw = value.strip()
        if not raw:
            raise serializers.ValidationError('Month must be in YYYY-MM or YYYY-MM-01 format.')
        if len(raw) == 7:
            try:
                parsed = datetime.strptime(raw, '%Y-%m').date()
            except ValueError:
                raise serializers.ValidationError('Month must be in YYYY-MM or YYYY-MM-01 format.')
            return parsed.replace(day=1)
        if len(raw) == 10:
            try:
                parsed = datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError('Month must be in YYYY-MM or YYYY-MM-01 format.')
            if parsed.day != 1:
                raise serializers.ValidationError('Month day must be 01 when provided with a full date.')
            return parsed
        raise serializers.ValidationError('Month must be in YYYY-MM or YYYY-MM-01 format.')

    def validate(self, attrs):
        has_date = attrs.get('date') is not None
        has_month = attrs.get('month') is not None
        if has_date == has_month:
            raise serializers.ValidationError("Provide exactly one of 'date' or 'month'.")
        return attrs


class ExpenseCycleUpdateSerializer(serializers.ModelSerializer):
    limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        help_text='Expense cycle limit. Must be greater than zero.',
    )

    class Meta:
        model = ExpenseCycle
        fields = ('limit', 'wallet', 'month', 'start_date', 'end_date')
        read_only_fields = ('wallet', 'month', 'start_date', 'end_date')

    def validate_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError('Limit must be greater than zero.')
        return value

    def validate(self, attrs):
        if any(field in self.initial_data for field in {'wallet', 'month', 'start_date', 'end_date'}):
            raise serializers.ValidationError("Only the 'limit' field can be updated.")
        return attrs


class ExpenseCycleCategorySpendingSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(read_only=True)
    category_name = serializers.CharField(read_only=True)
    category_icon = serializers.CharField(read_only=True)
    category_color = serializers.CharField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class ExpenseCycleBillingSummarySerializer(serializers.Serializer):
    total_cycle_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    spending_by_category = ExpenseCycleCategorySpendingSerializer(many=True, read_only=True)
    total_cycle_installment_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_cycle_recurring_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_future_installment_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_limit_per_day = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        read_only=True,
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('remaining_limit_per_day') is None:
            data.pop('remaining_limit_per_day', None)
        return data
