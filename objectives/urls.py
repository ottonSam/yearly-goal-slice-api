from django.urls import path

from .views import (
    ObjectiveByGoalCalendarListView,
    ObjectiveByTypeListView,
    ObjectiveCompleteView,
    ObjectiveCreateView,
    ObjectiveDetailView,
)


urlpatterns = [
    path('objectives/', ObjectiveCreateView.as_view(), name='objective-create'),
    path('objectives/type/<str:objective_type>/', ObjectiveByTypeListView.as_view(), name='objective-by-type'),
    path(
        'objectives/goal-calendar/<uuid:goal_calendar_id>/',
        ObjectiveByGoalCalendarListView.as_view(),
        name='objective-by-goal-calendar',
    ),
    path('objectives/<uuid:pk>/', ObjectiveDetailView.as_view(), name='objective-detail'),
    path('objectives/<uuid:pk>/complete/', ObjectiveCompleteView.as_view(), name='objective-complete'),
]
