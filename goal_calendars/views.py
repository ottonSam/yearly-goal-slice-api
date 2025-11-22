from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .models import GoalCalendar
from .serializers import GoalCalendarSerializer


class GoalCalendarListCreateView(generics.ListCreateAPIView):
    """
    Return calendars for the authenticated user and allow creation tied to the JWT user.
    """

    serializer_class = GoalCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]

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
