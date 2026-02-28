from calendar import monthrange
from datetime import date

from rest_framework import serializers

from wallets.models import Expense, ExpenseCategory, ExpenseCycle


def _add_one_month(base_date: date) -> date:
    year = base_date.year + (base_date.month // 12)
    month = (base_date.month % 12) + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


class ExpenseReadSerializer(serializers.ModelSerializer):
    expense_cycle = serializers.UUIDField(read_only=True, source='expense_cycle_id')
    expense_category = serializers.UUIDField(read_only=True, source='expense_category_id')
    installment_serie = serializers.UUIDField(read_only=True, source='installment_serie_id')
    recurring_root = serializers.UUIDField(read_only=True, source='recurring_root_id')

    class Meta:
        model = Expense
        fields = (
            'id',
            'expense_cycle',
            'expense_category',
            'installment_serie',
            'recurring_root',
            'description',
            'amount',
            'type',
            'date',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ExpenseCreateSerializer(serializers.ModelSerializer):
    expense_cycle = serializers.PrimaryKeyRelatedField(queryset=ExpenseCycle.objects.all())
    expense_category = serializers.PrimaryKeyRelatedField(queryset=ExpenseCategory.objects.all())
    description = serializers.CharField(max_length=120, required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    type = serializers.ChoiceField(
        choices=(Expense.TYPE_SINGLE, Expense.TYPE_RECURRING, Expense.TYPE_INSTALLMENT),
        required=True,
    )
    date = serializers.DateField(required=True)

    class Meta:
        model = Expense
        fields = (
            'id',
            'expense_cycle',
            'expense_category',
            'description',
            'amount',
            'type',
            'date',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_description(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError('Description is required.')
        return normalized

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        cycle = attrs['expense_cycle']
        category = attrs['expense_category']
        expense_type = attrs['type']
        expense_date = attrs['date']

        if cycle.wallet.user != user or not cycle.wallet.active:
            raise serializers.ValidationError({'expense_cycle': 'Expense cycle not found.'})
        if category.user != user:
            raise serializers.ValidationError({'expense_category': 'Expense category not found.'})
        if category.user_id != cycle.wallet.user_id:
            raise serializers.ValidationError(
                {'expense_category': 'Expense category must belong to the same wallet owner.'}
            )

        cycle_start = cycle.start_date
        cycle_next_month_start = _add_one_month(cycle_start)
        if not (cycle_start <= expense_date < cycle_next_month_start):
            raise serializers.ValidationError(
                {'date': 'Date must be on or after cycle start date and before the same day next month.'}
            )

        if expense_type == Expense.TYPE_INSTALLMENT:
            raise serializers.ValidationError(
                {'type': 'Installment expenses must be created by installment series.'}
            )

        return attrs


class ExpenseSingleUpdateSerializer(serializers.ModelSerializer):
    expense_category = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseCategory.objects.all(),
        required=False,
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    description = serializers.CharField(max_length=120, required=False)
    date = serializers.DateField(required=False)

    class Meta:
        model = Expense
        fields = ('expense_category', 'amount', 'description', 'date')

    def validate(self, attrs):
        if self.instance.type != Expense.TYPE_SINGLE:
            raise serializers.ValidationError(
                "Only expenses with type 'single_expense' can be edited directly."
            )

        allowed_fields = {'expense_category', 'amount', 'description', 'date'}
        sent_fields = set(self.initial_data.keys())
        if not sent_fields:
            raise serializers.ValidationError('At least one field must be provided.')
        if sent_fields - allowed_fields:
            raise serializers.ValidationError(
                "Only 'expense_category', 'amount', 'description' and 'date' can be updated for single expenses."
            )

        category = attrs.get('expense_category')
        if category is not None and category.user_id != self.instance.expense_cycle.wallet.user_id:
            raise serializers.ValidationError(
                {'expense_category': 'Expense category must belong to the same wallet owner.'}
            )

        amount = attrs.get('amount')
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({'amount': 'Amount must be greater than zero.'})

        description = attrs.get('description')
        if description is not None:
            normalized_description = description.strip()
            if not normalized_description:
                raise serializers.ValidationError({'description': 'Description is required.'})
            attrs['description'] = normalized_description

        expense_date = attrs.get('date')
        if expense_date is not None:
            cycle_start = self.instance.expense_cycle.start_date
            cycle_next_month_start = _add_one_month(cycle_start)
            if not (cycle_start <= expense_date < cycle_next_month_start):
                raise serializers.ValidationError(
                    {'date': 'Date must be on or after cycle start date and before the same day next month.'}
                )

        return attrs
