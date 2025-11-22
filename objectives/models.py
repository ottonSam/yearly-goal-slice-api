import uuid

from django.conf import settings
from django.db import models


class Objective(models.Model):
    class ObjectiveType(models.TextChoices):
        LONG_TERM = 'LONG_TERM', 'Long Term'
        MEDIUM_TERM = 'MEDIUM_TERM', 'Medium Term'
        GOAL_CALENDAR = 'GOAL_CALENDAR', 'Goal Calendar'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='objectives',
    )
    objective_type = models.CharField(max_length=20, choices=ObjectiveType.choices)
    goal_calendar = models.ForeignKey(
        'goal_calendars.GoalCalendar',
        on_delete=models.CASCADE,
        related_name='objectives',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'objective_type', 'title'],
                condition=models.Q(active=True),
                name='unique_active_objective_user_type_title',
            ),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_objective_type_display()})'
