from django.shortcuts import get_object_or_404
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
    WeeklyActivitySerializer,
)


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
        return GoalCalendarWeek.objects.filter(goal_calendar=calendar, active=True).order_by('week_num')


class WeeklyActivityBaseView:
    serializer_class = WeeklyActivitySerializer
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
        queryset = WeeklyActivity.objects.filter(goal_calendar=calendar, active=True)
        week_number = self.request.query_params.get('week_number')
        if week_number is not None:
            try:
                week_number_value = int(week_number)
            except ValueError:
                raise ValidationError({"week_number": "Week number must be an integer."})
            queryset = queryset.filter(week_number=week_number_value)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['goal_calendar'] = self.get_calendar()
        return context


class WeeklyActivityListCreateView(WeeklyActivityBaseView, generics.ListCreateAPIView):
    """
    List or create weekly activities for a specific goal calendar.
    """

    @swagger_auto_schema(
        operation_summary="List weekly activities",
        tags=["Weekly Activities"],
        manual_parameters=[
            openapi.Parameter(
                name='week_number',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Número da semana dentro do calendário (1..num_weeks)",
            ),
        ],
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
        serializer.save(goal_calendar=self.get_calendar())

    def get_queryset(self):
        week_number = self.request.query_params.get('week_number')
        if week_number is None:
            raise ValidationError({"week_number": "This query parameter is required to list activities for a week."})
        return super().get_queryset()


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
                    description="Dia concluído (monday..sunday); pode repetir o mesmo dia",
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
        manual_parameters=[
            openapi.Parameter(
                name='week_number',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Número da semana dentro do calendário (1..num_weeks)",
            ),
        ],
        responses={200: openapi.Response(description="Weekly report")},
    )
    def get(self, request, *args, **kwargs):
        activities = self.get_queryset()
        report_items = []

        for activity in activities:
            if activity.metric_type == WeeklyActivity.MetricType.FREQUENCY:
                target = activity.target_frequency or 0
                progress = (activity.frequency_progress / target * 100) if target else 0
            elif activity.metric_type == WeeklyActivity.MetricType.QUANTITY:
                target = activity.target_quantity or 0
                progress = (activity.quantity_progress / target * 100) if target else 0
            else:  # SPECIFIC_DAYS
                total_days = len(activity.specific_days or [])
                completed_days = len(set(str(d).lower() for d in activity.completed_days or []))
                progress = (completed_days / total_days * 100) if total_days else 0

            capped_progress = min(progress, 100)
            report_items.append(
                {
                    "activity_id": str(activity.id),
                    "title": activity.title,
                    "progress": round(capped_progress, 2),
                }
            )

        general_progress = round(sum(item["progress"] for item in report_items) / len(report_items), 2) if report_items else 0
        data = {"progress": report_items, "general_progress": general_progress}
        return Response(data, status=status.HTTP_200_OK)

    def get_queryset(self):
        week_number = self.request.query_params.get('week_number')
        if week_number is None:
            raise ValidationError({"week_number": "This query parameter is required to generate the report."})
        try:
            week_number_value = int(week_number)
        except ValueError:
            raise ValidationError({"week_number": "Week number must be an integer."})
        calendar = self.get_calendar()
        return WeeklyActivity.objects.filter(goal_calendar=calendar, active=True, week_number=week_number_value)
