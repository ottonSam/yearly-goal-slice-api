from rest_framework import serializers

from .models import Objective


class ObjectiveSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Objective
        fields = (
            'id',
            'user',
            'objective_type',
            'goal_calendar',
            'title',
            'description',
            'is_complete',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'is_complete', 'active', 'created_at', 'updated_at')

    def validate_goal_calendar(self, value):
        if value is None:
            return value

        request = self.context.get('request')
        if request and value.user != request.user:
            raise serializers.ValidationError("You cannot use calendars that belong to another user.")
        if not value.active:
            raise serializers.ValidationError("Goal calendar must be active.")
        return value

    def validate(self, attrs):
        objective_type = attrs.get('objective_type')

        if self.instance:
            objective_type = objective_type or self.instance.objective_type

        if 'goal_calendar' in attrs:
            goal_calendar = attrs['goal_calendar']
        elif self.instance:
            goal_calendar = self.instance.goal_calendar
        else:
            goal_calendar = None

        if objective_type == Objective.ObjectiveType.GOAL_CALENDAR and goal_calendar is None:
            raise serializers.ValidationError(
                {"goal_calendar": "This field is required for goal-calendar objectives."}
            )

        if objective_type != Objective.ObjectiveType.GOAL_CALENDAR and goal_calendar is not None:
            raise serializers.ValidationError(
                {"goal_calendar": "Goal calendar can only be set for goal-calendar objectives."}
            )

        request = self.context.get('request')
        user = request.user if request else None
        title = attrs.get('title')

        if self.instance:
            title = title or self.instance.title
            user = user or self.instance.user

        if user and objective_type and title:
            duplicate_qs = Objective.objects.filter(
                user=user,
                objective_type=objective_type,
                title=title,
                active=True,
            )
            if self.instance:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                raise serializers.ValidationError(
                    {"title": "You already have an active objective with this title for this type."}
                )

        return attrs
