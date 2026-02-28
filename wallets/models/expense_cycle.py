import uuid

from django.db import models


class ExpenseCycle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        'wallets.Wallet',
        on_delete=models.CASCADE,
        related_name='expense_cycles',
    )
    month = models.DateField(help_text='First day of the cycle month (YYYY-MM-01).')
    limit = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['wallet', 'month'],
                name='unique_expense_cycle_wallet_month',
            ),
            models.CheckConstraint(
                check=models.Q(limit__gt=0),
                name='expense_cycle_limit_gt_zero',
            ),
        ]

    def __str__(self):
        return f'{self.wallet.name} - {self.month.isoformat()}'
