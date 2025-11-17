from django.contrib import admin

from .models import GoalCalendar


@admin.register(GoalCalendar)
class GoalCalendarAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'start_date', 'num_weeks', 'active')
    list_filter = ('active',)
    search_fields = ('user__username',)
