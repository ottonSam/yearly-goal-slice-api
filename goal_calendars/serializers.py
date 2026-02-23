from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import GoalCalendar, GoalCalendarWeek, WeeklyActivity

ALLOWED_WEEK_DAYS = {
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday',
}


def get_activity_completion_percentage(activity):
    if activity.metric_type == WeeklyActivity.MetricType.FREQUENCY:
        target = activity.target_frequency or 0
        progress = (activity.frequency_progress / target * 100) if target else 0
    elif activity.metric_type == WeeklyActivity.MetricType.QUANTITY:
        target = activity.target_quantity or 0
        progress = (activity.quantity_progress / target * 100) if target else 0
    else:  # SPECIFIC_DAYS
        total_days = len(activity.specific_days or [])
        completed_days = len(set(str(day).lower() for day in activity.completed_days or []))
        progress = (completed_days / total_days * 100) if total_days else 0

    return round(min(progress, 100), 2)


class GoalCalendarBaseSerializer(serializers.ModelSerializer):
    end_date = serializers.SerializerMethodField(read_only=True)
    start_weekday = serializers.SerializerMethodField(read_only=True)
    end_weekday = serializers.SerializerMethodField(read_only=True)
    title = serializers.CharField(min_length=4, max_length=255, required=True)

    class Meta:
        model = GoalCalendar
        fields = (
            'id',
            'user',
            'title',
            'num_weeks',
            'start_date',
            'end_date',
            'start_weekday',
            'end_weekday',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'user',
            'end_date',
            'start_weekday',
            'end_weekday',
            'created_at',
            'updated_at',
        )

    def get_end_date(self, obj):
        return obj.get_end_date()

    def get_start_weekday(self, obj):
        return obj.start_date.strftime('%A').lower()

    def get_end_weekday(self, obj):
        return obj.get_end_date().strftime('%A').lower()

    def validate_start_date(self, value):
        today = timezone.localdate()
        if value < today:
            raise serializers.ValidationError("Start date cannot be in the past.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            calendar = GoalCalendar.objects.create(**validated_data)
            self._sync_weeks(calendar, calendar.start_date, calendar.num_weeks)
        return calendar

    def update(self, instance, validated_data):
        original_start_date = instance.start_date
        original_num_weeks = instance.num_weeks
        start_date = validated_data.get('start_date', instance.start_date)
        num_weeks = validated_data.get('num_weeks', instance.num_weeks)
        with transaction.atomic():
            calendar = super().update(instance, validated_data)
            if start_date != original_start_date or num_weeks != original_num_weeks:
                self._sync_weeks(calendar, start_date, num_weeks)
        return calendar

    def _sync_weeks(self, calendar, start_date, num_weeks):
        existing_weeks = {week.week_num: week for week in calendar.weeks.all()}

        for week_num in range(1, num_weeks + 1):
            week = existing_weeks.get(week_num)
            if week:
                changed = False
                if not week.active:
                    week.active = True
                    changed = True
                if changed:
                    week.save()
            else:
                GoalCalendarWeek.objects.create(
                    goal_calendar=calendar,
                    week_num=week_num,
                    active=True,
                )

        for week_num, week in existing_weeks.items():
            if week_num > num_weeks:
                changed = False
                if week.active:
                    week.active = False
                    changed = True
                if changed:
                    week.save()


class GoalCalendarWeekSerializer(serializers.ModelSerializer):
    start_week = serializers.SerializerMethodField(read_only=True)
    end_week = serializers.SerializerMethodField(read_only=True)
    average_completion_percentage = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GoalCalendarWeek
        fields = (
            'id',
            'week_num',
            'start_week',
            'end_week',
            'average_completion_percentage',
            'report',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_start_week(self, obj):
        return obj.get_start_week()

    def get_end_week(self, obj):
        return obj.get_end_week()

    def get_average_completion_percentage(self, obj):
        activities = getattr(obj, 'active_weekly_activities', None)
        if activities is None:
            activities = list(obj.weekly_activities.filter(active=True))
        else:
            activities = list(activities)

        if not activities:
            return 0

        completion_values = [get_activity_completion_percentage(activity) for activity in activities]
        return round(sum(completion_values) / len(completion_values), 2)


class GoalCalendarSerializer(GoalCalendarBaseSerializer):
    weeks = serializers.SerializerMethodField(read_only=True)

    class Meta(GoalCalendarBaseSerializer.Meta):
        fields = GoalCalendarBaseSerializer.Meta.fields + ('weeks',)
        read_only_fields = GoalCalendarBaseSerializer.Meta.read_only_fields + ('weeks',)

    def get_weeks(self, obj):
        weeks = obj.weeks.all().order_by('week_num')
        return GoalCalendarWeekSerializer(weeks, many=True).data


class GoalCalendarListSerializer(GoalCalendarBaseSerializer):
    pass


class WeeklyActivityAIReportRequestSerializer(serializers.Serializer):
    reflection = serializers.CharField(min_length=10, max_length=3000, required=True)



class WeeklyActivitySerializer(serializers.ModelSerializer):
    week = serializers.PrimaryKeyRelatedField(read_only=True)
    completion_percentage = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WeeklyActivity
        fields = (
            'id',
            'title',
            'description',
            'week',
            'metric_type',
            'target_frequency',
            'target_quantity',
            'specific_days',
            'frequency_progress',
            'quantity_progress',
            'completed_days',
            'completion_percentage',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'week',
            'frequency_progress',
            'quantity_progress',
            'completed_days',
            'completion_percentage',
            'active',
            'created_at',
            'updated_at',
        )

    def get_completion_percentage(self, obj):
        return get_activity_completion_percentage(obj)

    def validate(self, attrs):
        week = self.context.get('week')
        metric_type = attrs.get('metric_type')
        title = attrs.get('title')
        target_frequency = attrs.get('target_frequency') if 'target_frequency' in attrs else None
        target_quantity = attrs.get('target_quantity') if 'target_quantity' in attrs else None
        specific_days = attrs.get('specific_days') if 'specific_days' in attrs else None

        request = self.context.get('request')
        if week and request and week.goal_calendar.user != request.user:
            raise serializers.ValidationError({"week": "You cannot use weeks that belong to another user."})
        if week and not week.active:
            raise serializers.ValidationError({"week": "Week must be active."})
        if week and not week.goal_calendar.active:
            raise serializers.ValidationError({"week": "Goal calendar must be active."})

        if self.instance:
            if 'week' in attrs and attrs['week'] != self.instance.week:
                raise serializers.ValidationError({"week": "You cannot change the week of an activity."})
            week = week or self.instance.week
            metric_type = metric_type or self.instance.metric_type
            title = title or self.instance.title
            if 'target_frequency' not in attrs:
                target_frequency = self.instance.target_frequency
            if 'target_quantity' not in attrs:
                target_quantity = self.instance.target_quantity
            if 'specific_days' not in attrs:
                specific_days = self.instance.specific_days

        if week and title:
            existing = WeeklyActivity.objects.filter(week=week, title=title)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError({"title": "An activity with this title already exists for this week."})

        if metric_type == WeeklyActivity.MetricType.FREQUENCY:
            if target_frequency in (None, ''):
                raise serializers.ValidationError({"target_frequency": "Target frequency is required for this metric."})
            if target_frequency <= 0:
                raise serializers.ValidationError({"target_frequency": "Target frequency must be greater than zero."})
            if target_quantity not in (None, ''):
                raise serializers.ValidationError({"target_quantity": "This field is not used for frequency metrics."})
            if specific_days not in (None, [], ()):
                raise serializers.ValidationError({"specific_days": "This field is not used for frequency metrics."})

        elif metric_type == WeeklyActivity.MetricType.QUANTITY:
            if target_quantity in (None, ''):
                raise serializers.ValidationError({"target_quantity": "Target quantity is required for this metric."})
            if target_quantity <= 0:
                raise serializers.ValidationError({"target_quantity": "Target quantity must be greater than zero."})
            if target_frequency not in (None, ''):
                raise serializers.ValidationError({"target_frequency": "This field is not used for quantity metrics."})
            if specific_days not in (None, [], ()):
                raise serializers.ValidationError({"specific_days": "This field is not used for quantity metrics."})

        elif metric_type == WeeklyActivity.MetricType.SPECIFIC_DAYS:
            if not specific_days:
                raise serializers.ValidationError({"specific_days": "Provide at least one weekday for this metric."})
            if not isinstance(specific_days, (list, tuple)):
                raise serializers.ValidationError({"specific_days": "Specific days must be a list of weekdays."})
            normalized_days = [str(day).lower() for day in specific_days]
            invalid_days = [day for day in normalized_days if day not in ALLOWED_WEEK_DAYS]
            if invalid_days:
                raise serializers.ValidationError(
                    {"specific_days": f"Invalid weekday values: {', '.join(map(str, invalid_days))}."}
                )
            if target_frequency not in (None, '') or target_quantity not in (None, ''):
                raise serializers.ValidationError(
                    {"detail": "Frequency or quantity targets are not used for specific-days metrics."}
                )
            # Always store normalized weekday names.
            attrs['specific_days'] = normalized_days

        return attrs
