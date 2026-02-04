from django.contrib import admin

from .models import GoalCalendar, GoalCalendarWeek


@admin.register(GoalCalendar)
class GoalCalendarAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'start_date', 'num_weeks', 'active')
    list_filter = ('active',)
    search_fields = ('user__username',)


@admin.register(GoalCalendarWeek)
class GoalCalendarWeekAdmin(admin.ModelAdmin):
    list_display = ('id', 'goal_calendar', 'week_num', 'get_start_week', 'get_end_week', 'active')
    list_filter = ('active',)
    search_fields = ('goal_calendar__title', 'goal_calendar__user__username')

    def get_start_week(self, obj):
        return obj.get_start_week()

    get_start_week.short_description = 'start_week'

    def get_end_week(self, obj):
        return obj.get_end_week()

    get_end_week.short_description = 'end_week'
