import uuid

from django.db import models


class Expense(models.Model):
    TYPE_SINGLE = 'single_expense'
    TYPE_RECURRING = 'recurring_expense'
    TYPE_INSTALLMENT = 'installment_expense'

    TYPE_CHOICES = (
        (TYPE_SINGLE, 'Single expense'),
        (TYPE_RECURRING, 'Recurring expense'),
        (TYPE_INSTALLMENT, 'Installment expense'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_cycle = models.ForeignKey(
        'wallets.ExpenseCycle',
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    expense_category = models.ForeignKey(
        'wallets.ExpenseCategory',
        on_delete=models.PROTECT,
        related_name='expenses',
    )
    installment_serie = models.ForeignKey(
        'wallets.InstallmentSerie',
        on_delete=models.CASCADE,
        related_name='expenses',
        null=True,
        blank=True,
    )
    recurring_root = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='recurring_occurrences',
        null=True,
        blank=True,
    )
    recurring_canceled_from = models.DateField(
        null=True,
        blank=True,
        help_text='First day (YYYY-MM-01) from which recurring should not generate entries.',
    )
    description = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='expense_amount_gt_zero',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(type='installment_expense', installment_serie__isnull=False)
                    | ~models.Q(type='installment_expense')
                ),
                name='expense_installment_requires_installment_serie',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(type='installment_expense')
                    | models.Q(installment_serie__isnull=True)
                ),
                name='expense_non_installment_without_installment_serie',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(recurring_root__isnull=True)
                    | models.Q(type='recurring_expense')
                ),
                name='expense_recurring_root_only_for_recurring_type',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(recurring_root__isnull=True, recurring_canceled_from__isnull=True)
                    | models.Q(recurring_root__isnull=True, recurring_canceled_from__isnull=False)
                    | models.Q(recurring_root__isnull=False, recurring_canceled_from__isnull=True)
                ),
                name='expense_recurring_canceled_only_on_roots',
            ),
        ]

    def __str__(self):
        return f'{self.description} - {self.amount}'
