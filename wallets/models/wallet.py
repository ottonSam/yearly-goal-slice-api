import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallets',
    )
    name = models.CharField(max_length=80)
    limit = models.DecimalField(max_digits=12, decimal_places=2)
    cycle_limit_default = models.DecimalField(max_digits=12, decimal_places=2)
    cycle_starts = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message='Cycle start day must be between 1 and 31.'),
            MaxValueValidator(31, message='Cycle start day must be between 1 and 31.'),
        ]
    )
    cycle_ends = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message='Cycle end day must be between 1 and 31.'),
            MaxValueValidator(31, message='Cycle end day must be between 1 and 31.'),
        ]
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                condition=models.Q(active=True),
                name='unique_active_wallet_user_name',
            ),
            models.CheckConstraint(
                check=models.Q(limit__gt=0),
                name='wallet_limit_gt_zero',
            ),
            models.CheckConstraint(
                check=models.Q(cycle_limit_default__gt=0),
                name='wallet_cycle_limit_default_gt_zero',
            ),
            models.CheckConstraint(
                check=models.Q(limit__gte=models.F('cycle_limit_default')),
                name='wallet_limit_gte_cycle_limit_default',
            ),
            models.CheckConstraint(
                check=~models.Q(cycle_starts=models.F('cycle_ends')),
                name='wallet_cycle_starts_ne_cycle_ends',
            ),
        ]

    def __str__(self):
        return f'{self.name} - {self.user.username}'
