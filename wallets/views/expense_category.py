from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, permissions, viewsets

from wallets.models import ExpenseCategory
from wallets.permissions import IsOwner
from wallets.serializers import ExpenseCategoryCreateUpdateSerializer, ExpenseCategoryReadSerializer


EXPENSE_CATEGORY_CREATE_EXAMPLE = {
    'name': 'Alimentação',
    'icon': 'mdi:food',
    'color': '#FF6B00',
}

EXPENSE_CATEGORY_PATCH_EXAMPLE = {
    'color': '#00C2FF',
}


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'}:
            return ExpenseCategoryReadSerializer
        return ExpenseCategoryCreateUpdateSerializer

    @swagger_auto_schema(
        operation_summary='Create expense category',
        operation_description='Creates an expense category for the authenticated user.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'icon', 'color'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, max_length=60),
                'icon': openapi.Schema(type=openapi.TYPE_STRING, max_length=80),
                'color': openapi.Schema(type=openapi.TYPE_STRING, max_length=32),
            },
            example=EXPENSE_CATEGORY_CREATE_EXAMPLE,
        ),
        responses={201: ExpenseCategoryReadSerializer},
        tags=['Wallet Expense Categories'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Partially update expense category',
        operation_description='Partially updates an expense category owned by the authenticated user.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, max_length=60),
                'icon': openapi.Schema(type=openapi.TYPE_STRING, max_length=80),
                'color': openapi.Schema(type=openapi.TYPE_STRING, max_length=32),
            },
            example=EXPENSE_CATEGORY_PATCH_EXAMPLE,
        ),
        responses={200: ExpenseCategoryReadSerializer},
        tags=['Wallet Expense Categories'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Delete expense category',
        operation_description='Deletes an expense category owned by the authenticated user.',
        request_body=None,
        tags=['Wallet Expense Categories'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
