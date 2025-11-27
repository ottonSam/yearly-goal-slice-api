import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class GoalCalendar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="Goal calendar")
    num_weeks = models.PositiveIntegerField(
        default=12,
        validators=[MinValueValidator(1), MaxValueValidator(53)],
    )
    start_date = models.DateField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.num_weeks}-week calendar for {self.user.username}'

    def get_end_date(self):
        return self.start_date + timedelta(weeks=self.num_weeks)

    class Meta:
        ordering = ['-start_date']


class WeeklyActivity(models.Model):
    class MetricType(models.TextChoices):
        FREQUENCY = 'FREQUENCY', 'Frequency'
        QUANTITY = 'QUANTITY', 'Quantity'
        SPECIFIC_DAYS = 'SPECIFIC_DAYS', 'Specific days'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goal_calendar = models.ForeignKey(
        GoalCalendar,
        on_delete=models.CASCADE,
        related_name='weekly_activities',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    week_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    metric_type = models.CharField(max_length=20, choices=MetricType.choices)
    target_frequency = models.PositiveIntegerField(null=True, blank=True)
    target_quantity = models.PositiveIntegerField(null=True, blank=True)
    specific_days = models.JSONField(default=list, blank=True)
    frequency_progress = models.PositiveIntegerField(default=0)
    quantity_progress = models.PositiveIntegerField(default=0)
    completed_days = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['week_number', 'title']

    def __str__(self):
        return f'{self.title} (Week {self.week_number} - {self.goal_calendar})'
