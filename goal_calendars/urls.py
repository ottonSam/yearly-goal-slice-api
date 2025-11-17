from django.urls import path

from .views import GoalCalendarDetailView, GoalCalendarListCreateView


urlpatterns = [
    path('goal-calendars/', GoalCalendarListCreateView.as_view(), name='goal-calendar-list-create'),
    path('goal-calendars/<uuid:pk>/', GoalCalendarDetailView.as_view(), name='goal-calendar-detail'),
]
