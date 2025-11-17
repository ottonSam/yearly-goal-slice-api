from django.apps import AppConfig


class GoalCalendarsConfig(AppConfig):
    default_auto_field = 'yearly_goal_slice.fields.UUIDAutoField'
    name = 'goal_calendars'
