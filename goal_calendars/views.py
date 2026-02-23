from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import GoalCalendar, GoalCalendarWeek, WeeklyActivity
from .serializers import (
    ALLOWED_WEEK_DAYS,
    GoalCalendarListSerializer,
    GoalCalendarSerializer,
    GoalCalendarWeekSerializer,
    WeeklyActivityAIReportRequestSerializer,
    WeeklyActivitySerializer,
    get_activity_completion_percentage,
)
from .services import DeepSeekWeeklyReportService


class WeeklyActivityMetricTypeListView(generics.GenericAPIView):
    """
    List available weekly activity metric types.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="List activity metric types", tags=["Weekly Activities"], request_body=None)
    def get(self, request, *args, **kwargs):
        metric_types = [
            {"value": value, "label": label}
            for value, label in WeeklyActivity.MetricType.choices
        ]
        return Response({"metric_types": metric_types}, status=status.HTTP_200_OK)


class GoalCalendarListCreateView(generics.ListCreateAPIView):
    """
    Return calendars for the authenticated user and allow creation tied to the JWT user.
    """

    serializer_class = GoalCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return GoalCalendarListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return GoalCalendar.objects.filter(user=self.request.user, active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalCalendarDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve or update a calendar if it belongs to the authenticated user.
    """

    serializer_class = GoalCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'delete']

    def get_queryset(self):
        return GoalCalendar.objects.filter(user=self.request.user, active=True)

    def perform_update(self, serializer):
        calendar = self.get_object()
        if calendar.user != self.request.user:
            raise PermissionDenied("You cannot modify calendars that belong to other users.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("You cannot delete calendars that belong to other users.")
        instance.active = False
        instance.save(update_fields=["active"])


class GoalCalendarWeekListView(generics.ListAPIView):
    """
    List active weeks for a specific goal calendar.
    """

    serializer_class = GoalCalendarWeekSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_calendar(self):
        return get_object_or_404(
            GoalCalendar,
            id=self.kwargs['goal_calendar_id'],
            user=self.request.user,
            active=True,
        )

    def get_queryset(self):
        calendar = self.get_calendar()
        return (
            GoalCalendarWeek.objects.filter(goal_calendar=calendar, active=True)
            .prefetch_related(
                Prefetch(
                    'weekly_activities',
                    queryset=WeeklyActivity.objects.filter(active=True),
                    to_attr='active_weekly_activities',
                )
            )
            .order_by('week_num')
        )


class WeeklyActivityBaseView:
    serializer_class = WeeklyActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_week(self):
        return get_object_or_404(
            GoalCalendarWeek,
            id=self.kwargs['week_id'],
            goal_calendar__user=self.request.user,
            goal_calendar__active=True,
            active=True,
        )

    def get_queryset(self):
        week = self.get_week()
        return WeeklyActivity.objects.filter(week=week, active=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['week'] = self.get_week()
        return context

    def build_activity_progress(self, activities):
        progress_items = []
        for activity in activities:
            progress_items.append(
                {
                    "activity_id": str(activity.id),
                    "title": activity.title,
                    "metric_type": activity.metric_type,
                    "completion_percentage": get_activity_completion_percentage(activity),
                    "completed_days": [str(day).lower() for day in (activity.completed_days or [])],
                }
            )
        return progress_items

    def get_general_progress(self, progress_items):
        if not progress_items:
            return 0
        return round(
            sum(item["completion_percentage"] for item in progress_items) / len(progress_items),
            2,
        )


class WeeklyActivityListCreateView(WeeklyActivityBaseView, generics.ListCreateAPIView):
    """
    List or create weekly activities for a specific week.
    """

    @swagger_auto_schema(
        operation_summary="List weekly activities",
        tags=["Weekly Activities"],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create weekly activity",
        tags=["Weekly Activities"],
        request_body=WeeklyActivitySerializer,
    )
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(week=self.get_week())


class WeeklyActivityDetailView(WeeklyActivityBaseView, generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a weekly activity tied to a calendar.
    """
    http_method_names = ['get', 'put']

    @swagger_auto_schema(operation_summary="Retrieve weekly activity", tags=["Weekly Activities"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @swagger_auto_schema(operation_summary="Update weekly activity", tags=["Weekly Activities"])
    def put(self, *args, **kwargs):
        return super().put(*args, **kwargs)

    @swagger_auto_schema(operation_summary="Partial update weekly activity", tags=["Weekly Activities"])
    def patch(self, *args, **kwargs):
        return super().patch(*args, **kwargs)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])


class WeeklyActivityProgressBaseView(WeeklyActivityBaseView, generics.GenericAPIView):
    """
    Base for metric-specific progress endpoints.
    """

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])


class WeeklyActivityFrequencyProgressView(WeeklyActivityProgressBaseView):
    """
    Increment frequency progress for FREQUENCY metric activities.
    """

    @swagger_auto_schema(
        operation_summary="Add frequency progress",
        tags=["Weekly Activities"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['day'],
            properties={
                'day': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Dia concluído (monday..sunday); não permite repetir o mesmo dia na semana",
                    enum=sorted(list(ALLOWED_WEEK_DAYS)),
                ),
            },
        ),
    )
    def post(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.metric_type != WeeklyActivity.MetricType.FREQUENCY:
            raise ValidationError({"detail": "This activity does not use frequency metric."})

        day = request.data.get('day')
        if not day:
            raise ValidationError({"day": "Day is required."})
        day_normalized = str(day).lower()
        if day_normalized not in ALLOWED_WEEK_DAYS:
            raise ValidationError({"day": "Invalid weekday value."})

        completed = list(activity.completed_days or [])
        if day_normalized in [str(d).lower() for d in completed]:
            raise ValidationError({"day": "This day has already been marked for this activity."})

        completed.append(day_normalized)
        activity.completed_days = completed
        activity.frequency_progress += 1
        activity.save(update_fields=['completed_days', 'frequency_progress', 'updated_at'])
        return Response(self.get_serializer(activity).data, status=status.HTTP_200_OK)


class WeeklyActivityQuantityProgressView(WeeklyActivityProgressBaseView):
    """
    Increment quantity progress for QUANTITY metric activities.
    """

    @swagger_auto_schema(
        operation_summary="Add quantity progress",
        tags=["Weekly Activities"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, default=1, description="Quantidade a somar ao progresso"),
            },
        ),
    )
    def post(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.metric_type != WeeklyActivity.MetricType.QUANTITY:
            raise ValidationError({"detail": "This activity does not use quantity metric."})

        amount = request.data.get('amount', 1)
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValidationError({"amount": "Amount must be an integer."})
        if amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})

        activity.quantity_progress += amount
        activity.save(update_fields=['quantity_progress', 'updated_at'])
        return Response(self.get_serializer(activity).data, status=status.HTTP_200_OK)


class WeeklyActivitySpecificDaysProgressView(WeeklyActivityProgressBaseView):
    """
    Mark a day as completed for SPECIFIC_DAYS metric activities.
    """

    @swagger_auto_schema(
        operation_summary="Mark specific day done",
        tags=["Weekly Activities"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['day'],
            properties={
                'day': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Dia concluído (monday..sunday)",
                    enum=sorted(list(ALLOWED_WEEK_DAYS)),
                ),
            },
        ),
    )
    def post(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.metric_type != WeeklyActivity.MetricType.SPECIFIC_DAYS:
            raise ValidationError({"detail": "This activity does not use specific-days metric."})

        day = request.data.get('day')
        if not day:
            raise ValidationError({"day": "Day is required."})
        day_normalized = str(day).lower()
        if day_normalized not in ALLOWED_WEEK_DAYS:
            raise ValidationError({"day": "Invalid weekday value."})
        allowed_days = [str(d).lower() for d in activity.specific_days]
        if day_normalized not in allowed_days:
            raise ValidationError({"day": "This day is not configured for this activity."})

        completed = list(activity.completed_days or [])
        if day_normalized in [str(d).lower() for d in completed]:
            raise ValidationError({"day": "This day has already been marked for this activity."})

        completed.append(day_normalized)
        activity.completed_days = completed
        activity.save(update_fields=['completed_days', 'updated_at'])
        return Response(self.get_serializer(activity).data, status=status.HTTP_200_OK)


class WeeklyActivityWeekReportView(WeeklyActivityBaseView, generics.GenericAPIView):
    """
    Generate a weekly performance report aggregating activity progress for a given week.
    """

    @swagger_auto_schema(
        operation_summary="Weekly performance report",
        tags=["Weekly Activities"],
        responses={200: openapi.Response(description="Weekly report")},
    )
    def get(self, request, *args, **kwargs):
        activities = self.get_queryset()
        progress_items = self.build_activity_progress(activities)
        report_items = [
            {
                "activity_id": item["activity_id"],
                "title": item["title"],
                "progress": item["completion_percentage"],
            }
            for item in progress_items
        ]
        data = {"progress": report_items, "general_progress": self.get_general_progress(progress_items)}
        return Response(data, status=status.HTTP_200_OK)


class WeeklyActivityAIWeekReportView(WeeklyActivityBaseView, generics.GenericAPIView):
    serializer_class = WeeklyActivityAIReportRequestSerializer

    @swagger_auto_schema(
        operation_summary="Generate weekly AI report",
        tags=["Weekly Activities"],
        request_body=WeeklyActivityAIReportRequestSerializer,
        responses={200: openapi.Response(description="AI weekly report generated")},
    )
    def post(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        week = self.get_week()
        today = timezone.localdate()
        week_end = week.get_end_week()
        if today < week_end:
            raise ValidationError(
                {
                    "detail": "AI report can only be generated on or after the final day of the week.",
                    "week_end": str(week_end),
                    "today": str(today),
                }
            )
        if (week.report or "").strip():
            raise ValidationError({"detail": "This week report has already been generated."})

        current_activities = list(self.get_queryset())
        current_progress = self.build_activity_progress(current_activities)
        current_general_progress = self.get_general_progress(current_progress)

        previous_weeks = (
            GoalCalendarWeek.objects.filter(
                goal_calendar=week.goal_calendar,
                active=True,
                week_num__lt=week.week_num,
            )
            .prefetch_related(
                Prefetch(
                    'weekly_activities',
                    queryset=WeeklyActivity.objects.filter(active=True),
                    to_attr='active_weekly_activities',
                )
            )
            .order_by('-week_num')[:3]
        )

        previous_reports = []
        for previous_week in previous_weeks:
            previous_progress_items = self.build_activity_progress(
                list(getattr(previous_week, 'active_weekly_activities', []))
            )
            previous_reports.append(
                {
                    "week_id": str(previous_week.id),
                    "week_num": previous_week.week_num,
                    "start_week": str(previous_week.get_start_week()),
                    "end_week": str(previous_week.get_end_week()),
                    "average_completion_percentage": self.get_general_progress(previous_progress_items),
                    "report": previous_week.report or "",
                }
            )

        if previous_reports:
            previous_average_progress = round(
                sum(item["average_completion_percentage"] for item in previous_reports) / len(previous_reports),
                2,
            )
            progress_delta = round(current_general_progress - previous_average_progress, 2)
        else:
            previous_average_progress = 0
            progress_delta = 0

        if progress_delta > 0.5:
            trend = "up"
        elif progress_delta < -0.5:
            trend = "down"
        else:
            trend = "stable"

        prompt_context = {
            "goal_calendar_id": str(week.goal_calendar.id),
            "goal_calendar_title": week.goal_calendar.title,
            "goal_calendar_num_weeks": week.goal_calendar.num_weeks,
            "year_goal_method": "1 ano dividido em ciclos de 12 semanas",
            "good_performance_threshold_percentage": 85,
            "week_id": str(week.id),
            "week_num": week.week_num,
            "week_start": str(week.get_start_week()),
            "week_end": str(week.get_end_week()),
            "user_reflection": input_serializer.validated_data["reflection"],
            "current_week_general_completion_percentage": current_general_progress,
            "current_week_activities": current_progress,
            "last_three_weeks_reports": previous_reports,
            "last_three_weeks_average_completion_percentage": previous_average_progress,
            "trend_vs_last_three_weeks_percentage_points": progress_delta,
            "trend": trend,
        }

        try:
            ai_report = DeepSeekWeeklyReportService().generate_week_report(prompt_context)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            return Response(
                {"detail": "Could not generate AI report right now."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        week.report = ai_report
        week.save(update_fields=["report", "updated_at"])

        data = {
            "week_id": str(week.id),
            "week_num": week.week_num,
            "general_progress": current_general_progress,
            "last_three_weeks_average_progress": previous_average_progress,
            "trend_vs_last_three_weeks": progress_delta,
            "trend": trend,
            "activities": current_progress,
            "last_three_weeks_reports": previous_reports,
            "report": ai_report,
        }
        return Response(data, status=status.HTTP_200_OK)
