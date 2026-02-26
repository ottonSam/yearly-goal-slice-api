from rest_framework.permissions import BasePermission


class IsWalletOwner(BasePermission):
    message = 'You do not have permission to access this wallet.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
