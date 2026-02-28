from rest_framework import serializers

from wallets.models import ExpenseCategory, InstallmentSerie, Wallet


class InstallmentSerieReadSerializer(serializers.ModelSerializer):
    wallet = serializers.UUIDField(read_only=True, source='wallet_id')
    expense_category = serializers.UUIDField(read_only=True, source='expense_category_id')
    expenses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InstallmentSerie
        fields = (
            'id',
            'wallet',
            'expense_category',
            'description',
            'total_amount',
            'installments_count',
            'start_date',
            'active',
            'expenses_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class InstallmentSerieCreateUpdateSerializer(serializers.ModelSerializer):
    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    expense_category = serializers.PrimaryKeyRelatedField(queryset=ExpenseCategory.objects.all())
    description = serializers.CharField(max_length=120, required=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    installments_count = serializers.IntegerField(min_value=1, required=True)
    start_date = serializers.DateField(required=True)

    class Meta:
        model = InstallmentSerie
        fields = (
            'id',
            'wallet',
            'expense_category',
            'description',
            'total_amount',
            'installments_count',
            'start_date',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_description(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError('Description is required.')
        return normalized

    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Total amount must be greater than zero.')
        return value

    def validate(self, attrs):
        wallet = attrs.get('wallet') or getattr(self.instance, 'wallet', None)
        category = attrs.get('expense_category') or getattr(self.instance, 'expense_category', None)

        request = self.context.get('request')
        user = request.user if request else None

        if wallet is not None and (wallet.user != user or not wallet.active):
            raise serializers.ValidationError({'wallet': 'Wallet not found.'})

        if category is not None and category.user != user:
            raise serializers.ValidationError({'expense_category': 'Expense category not found.'})

        if wallet is not None and category is not None and wallet.user_id != category.user_id:
            raise serializers.ValidationError(
                {'expense_category': 'Expense category must belong to wallet owner.'}
            )

        return attrs
