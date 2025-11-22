from django.utils import timezone
from rest_framework import serializers

from .models import GoalCalendar


class GoalCalendarSerializer(serializers.ModelSerializer):
    end_date = serializers.SerializerMethodField(read_only=True)
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
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'end_date', 'created_at', 'updated_at')

    def get_end_date(self, obj):
        return obj.get_end_date()

    def validate_start_date(self, value):
        today = timezone.localdate()
        if value < today:
            raise serializers.ValidationError("Start date cannot be in the past.")
        return value
