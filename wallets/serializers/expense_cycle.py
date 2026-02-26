from datetime import datetime

from rest_framework import serializers

from wallets.models import ExpenseCycle


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
