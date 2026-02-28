import uuid

from django.db import models


class InstallmentSerie(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        'wallets.Wallet',
        on_delete=models.CASCADE,
        related_name='installment_series',
    )
    expense_category = models.ForeignKey(
        'wallets.ExpenseCategory',
        on_delete=models.PROTECT,
        related_name='installment_series',
    )
    description = models.CharField(max_length=120)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    installments_count = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_amount__gt=0),
                name='installment_serie_total_amount_gt_zero',
            ),
            models.CheckConstraint(
                check=models.Q(installments_count__gte=1),
                name='installment_serie_installments_count_gte_one',
            ),
        ]

    def __str__(self):
        return f'{self.description} - {self.installments_count}x'
