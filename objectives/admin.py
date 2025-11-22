from django.contrib import admin

from .models import Objective


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ('title', 'objective_type', 'user', 'goal_calendar', 'is_complete', 'active')
    list_filter = ('objective_type', 'is_complete', 'active')
    search_fields = ('title', 'description', 'user__email')
    autocomplete_fields = ('user', 'goal_calendar')
