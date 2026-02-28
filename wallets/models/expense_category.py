import uuid

from django.conf import settings
from django.db import models
from django.db.models import F
from django.db.models.functions import Lower


class ExpenseCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expense_categories',
    )
    name = models.CharField(max_length=60)
    icon = models.CharField(max_length=80)
    color = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                F('user'),
                Lower('name'),
                name='unique_expense_category_user_name_ci',
            ),
        ]

    def __str__(self):
        return f'{self.name} - {self.user.username}'
