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
        # End date is inclusive: last day of the final week.
        return self.start_date + timedelta(days=(self.num_weeks * 7) - 1)

    class Meta:
        ordering = ['-start_date']


class GoalCalendarWeek(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goal_calendar = models.ForeignKey(
        GoalCalendar,
        on_delete=models.CASCADE,
        related_name='weeks',
    )
    week_num = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    report = models.TextField(blank=True, null=True, default=None)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['week_num']
        constraints = [
            models.UniqueConstraint(
                fields=['goal_calendar', 'week_num'],
                name='unique_goal_calendar_week_num',
            ),
        ]

    def __str__(self):
        return f'Week {self.week_num} - {self.goal_calendar}'

    def get_start_week(self):
        return self.goal_calendar.start_date + timedelta(days=(self.week_num - 1) * 7)

    def get_end_week(self):
        # End of week is inclusive (start + 6 days).
        return self.get_start_week() + timedelta(days=6)


class WeeklyActivity(models.Model):
    class MetricType(models.TextChoices):
        FREQUENCY = 'FREQUENCY', 'Frequency'
        QUANTITY = 'QUANTITY', 'Quantity'
        SPECIFIC_DAYS = 'SPECIFIC_DAYS', 'Specific days'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    week = models.ForeignKey(
        GoalCalendarWeek,
        on_delete=models.CASCADE,
        related_name='weekly_activities',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(
                fields=['week', 'title'],
                name='unique_week_activity_title',
            ),
        ]

    def __str__(self):
        return f'{self.title} (Week {self.week.week_num} - {self.week.goal_calendar})'
