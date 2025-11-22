from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from goal_calendars.models import GoalCalendar
from .models import Objective
from .serializers import ObjectiveSerializer


class ObjectiveBaseView:
    serializer_class = ObjectiveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Objective.objects.filter(user=self.request.user, active=True)


class ObjectiveListCreateView(ObjectiveBaseView, generics.ListCreateAPIView):
    """
    List or create objectives for the authenticated user.
    """

    @swagger_auto_schema(operation_summary="List objectives", tags=["Objectives"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @swagger_auto_schema(operation_summary="Create objective", tags=["Objectives"])
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ObjectiveByTypeListView(ObjectiveBaseView, generics.ListAPIView):
    """
    List active objectives filtered by type.
    """

    @swagger_auto_schema(operation_summary="List objectives by type", tags=["Objectives"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def get_queryset(self):
        objective_type = self.kwargs['objective_type'].upper()
        if objective_type not in Objective.ObjectiveType.values:
            raise ValidationError({"objective_type": "Invalid objective type."})
        return super().get_queryset().filter(objective_type=objective_type)


class ObjectiveByGoalCalendarListView(ObjectiveBaseView, generics.ListAPIView):
    """
    List objectives tied to a specific goal calendar.
    """

    @swagger_auto_schema(operation_summary="List objectives by calendar", tags=["Objectives"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def get_queryset(self):
        calendar = get_object_or_404(
            GoalCalendar,
            id=self.kwargs['goal_calendar_id'],
            user=self.request.user,
            active=True,
        )
        return super().get_queryset().filter(
            objective_type=Objective.ObjectiveType.GOAL_CALENDAR,
            goal_calendar=calendar,
        )


class ObjectiveDetailView(ObjectiveBaseView, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, edit or soft-delete an objective.
    """

    @swagger_auto_schema(operation_summary="Retrieve objective", tags=["Objectives"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @swagger_auto_schema(operation_summary="Update objective", tags=["Objectives"])
    def put(self, *args, **kwargs):
        return super().put(*args, **kwargs)

    @swagger_auto_schema(operation_summary="Partially update objective", tags=["Objectives"])
    def patch(self, *args, **kwargs):
        return super().patch(*args, **kwargs)

    @swagger_auto_schema(operation_summary="Soft delete objective", tags=["Objectives"])
    def delete(self, *args, **kwargs):
        return super().delete(*args, **kwargs)

    def perform_destroy(self, instance):
        instance.active = False
        instance.save(update_fields=['active'])


class ObjectiveCompleteView(ObjectiveBaseView, generics.GenericAPIView):
    """
    Mark an objective as completed.
    """

    @swagger_auto_schema(operation_summary="Complete objective", tags=["Objectives"], request_body=None)
    def post(self, request, *args, **kwargs):
        objective = self.get_object()
        if not objective.is_complete:
            objective.is_complete = True
            objective.save(update_fields=['is_complete'])
        serializer = self.get_serializer(objective)
        return Response(serializer.data, status=status.HTTP_200_OK)
