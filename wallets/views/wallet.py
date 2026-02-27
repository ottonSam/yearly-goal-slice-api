from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from rest_framework import filters, permissions, viewsets

from wallets.models import Wallet
from wallets.permissions import IsOwner
from wallets.serializers import WalletCreateUpdateSerializer, WalletReadSerializer


WALLET_CREATE_EXAMPLE = {
    'name': 'Main Wallet',
    'limit': '5000.00',
    'cycle_limit_default': '3000.00',
    'cycle_starts': 25,
    'cycle_ends': 9,
}

WALLET_PATCH_EXAMPLE = {
    'name': 'Main Wallet Updated',
    'cycle_limit_default': '3200.00',
    'cycle_ends': 10,
}


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_summary='List wallets',
        tags=['Wallets'],
    ),
)
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        operation_summary='Retrieve wallet',
        tags=['Wallets'],
    ),
)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema(
        operation_summary='Update wallet',
        tags=['Wallets'],
    ),
)
class WalletViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user, active=True)

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'}:
            return WalletReadSerializer
        return WalletCreateUpdateSerializer

    @swagger_auto_schema(
        operation_summary='Create wallet',
        operation_description='Creates a wallet for the authenticated user.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'limit', 'cycle_limit_default', 'cycle_starts', 'cycle_ends'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, max_length=80),
                'limit': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'cycle_limit_default': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'cycle_starts': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=31),
                'cycle_ends': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=31),
            },
            example=WALLET_CREATE_EXAMPLE,
        ),
        responses={201: WalletReadSerializer},
        tags=['Wallets'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Partially update wallet',
        operation_description='Partially updates a wallet owned by the authenticated user.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, max_length=80),
                'limit': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'cycle_limit_default': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'cycle_starts': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=31),
                'cycle_ends': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=31),
            },
            example=WALLET_PATCH_EXAMPLE,
        ),
        responses={200: WalletReadSerializer},
        tags=['Wallets'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Delete wallet',
        operation_description='Soft delete: marks wallet as inactive.',
        request_body=None,
        tags=['Wallets'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.active = False
        instance.save(update_fields=['active', 'updated_at'])
