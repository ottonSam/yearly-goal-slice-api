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

    class Meta:
        model = GoalCalendarWeek
        fields = (
            'id',
            'week_num',
            'start_week',
            'end_week',
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



class WeeklyActivitySerializer(serializers.ModelSerializer):
    goal_calendar = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = WeeklyActivity
        fields = (
            'id',
            'goal_calendar',
            'title',
            'description',
            'week_number',
            'metric_type',
            'target_frequency',
            'target_quantity',
            'specific_days',
            'frequency_progress',
            'quantity_progress',
            'completed_days',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'goal_calendar',
            'frequency_progress',
            'quantity_progress',
            'completed_days',
            'active',
            'created_at',
            'updated_at',
        )

    def validate_goal_calendar(self, value):
        request = self.context.get('request')
        if request and value and value.user != request.user:
            raise serializers.ValidationError("You cannot use calendars that belong to another user.")
        if value and not value.active:
            raise serializers.ValidationError("Goal calendar must be active.")
        return value

    def validate(self, attrs):
        goal_calendar = attrs.get('goal_calendar') or self.context.get('goal_calendar')
        week_number = attrs.get('week_number')
        metric_type = attrs.get('metric_type')
        target_frequency = attrs.get('target_frequency') if 'target_frequency' in attrs else None
        target_quantity = attrs.get('target_quantity') if 'target_quantity' in attrs else None
        specific_days = attrs.get('specific_days') if 'specific_days' in attrs else None

        request = self.context.get('request')
        if goal_calendar and request and goal_calendar.user != request.user:
            raise serializers.ValidationError({"goal_calendar": "You cannot use calendars that belong to another user."})

        if self.instance:
            if 'goal_calendar' in attrs and attrs['goal_calendar'] != self.instance.goal_calendar:
                raise serializers.ValidationError({"goal_calendar": "You cannot change the calendar of an activity."})
            goal_calendar = goal_calendar or self.instance.goal_calendar
            week_number = week_number or self.instance.week_number
            metric_type = metric_type or self.instance.metric_type
            if 'target_frequency' not in attrs:
                target_frequency = self.instance.target_frequency
            if 'target_quantity' not in attrs:
                target_quantity = self.instance.target_quantity
            if 'specific_days' not in attrs:
                specific_days = self.instance.specific_days

        if goal_calendar and week_number:
            if week_number < 1 or week_number > goal_calendar.num_weeks:
                raise serializers.ValidationError(
                    {"week_number": f"Week number must be between 1 and {goal_calendar.num_weeks} for this calendar."}
                )

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
