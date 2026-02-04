from django.urls import path

from .views import (
    GoalCalendarDetailView,
    GoalCalendarListCreateView,
    GoalCalendarWeekListView,
    WeeklyActivityDetailView,
    WeeklyActivityListCreateView,
    WeeklyActivityFrequencyProgressView,
    WeeklyActivityQuantityProgressView,
    WeeklyActivitySpecificDaysProgressView,
    WeeklyActivityMetricTypeListView,
    WeeklyActivityWeekReportView,
)


urlpatterns = [
    path('goal-calendars/', GoalCalendarListCreateView.as_view(), name='goal-calendar-list-create'),
    path('goal-calendars/<uuid:pk>/', GoalCalendarDetailView.as_view(), name='goal-calendar-detail'),
    path(
        'goal-calendars/<uuid:goal_calendar_id>/weeks/',
        GoalCalendarWeekListView.as_view(),
        name='goal-calendar-week-list',
    ),
    path(
        'goal-calendars/activities/metric-types/',
        WeeklyActivityMetricTypeListView.as_view(),
        name='weekly-activity-metric-type-list',
    ),
    path(
        'goal-calendars/weeks/<uuid:week_id>/activities/',
        WeeklyActivityListCreateView.as_view(),
        name='weekly-activity-list-create',
    ),
    path(
        'goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/',
        WeeklyActivityDetailView.as_view(),
        name='weekly-activity-detail',
    ),
    path(
        'goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/progress/frequency/',
        WeeklyActivityFrequencyProgressView.as_view(),
        name='weekly-activity-progress-frequency',
    ),
    path(
        'goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/progress/quantity/',
        WeeklyActivityQuantityProgressView.as_view(),
        name='weekly-activity-progress-quantity',
    ),
    path(
        'goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/progress/specific-days/',
        WeeklyActivitySpecificDaysProgressView.as_view(),
        name='weekly-activity-progress-specific-days',
    ),
    path(
        'goal-calendars/weeks/<uuid:week_id>/activities/report/',
        WeeklyActivityWeekReportView.as_view(),
        name='weekly-activity-week-report',
    ),
]
