from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    message = 'You do not have permission to access this resource.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, 'user', None)
        if owner is not None:
            return owner == request.user
        wallet = getattr(obj, 'wallet', None)
        if wallet is not None:
            return wallet.user == request.user
        return False


# Backward-compatible alias
IsWalletOwner = IsOwner
