from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from wallets.models import Expense
from wallets.permissions import IsOwner
from wallets.serializers import ExpenseCreateSerializer, ExpenseReadSerializer
from wallets.services.expense import sync_recurring_expense_to_existing_cycles


EXPENSE_CREATE_SINGLE_EXAMPLE = {
    'expense_cycle': '00000000-0000-0000-0000-000000000000',
    'expense_category': '00000000-0000-0000-0000-000000000000',
    'description': 'Mercado',
    'amount': '150.00',
    'type': 'single_expense',
    'date': '2026-03-02',
}

EXPENSE_CREATE_RECURRING_EXAMPLE = {
    'expense_cycle': '00000000-0000-0000-0000-000000000000',
    'expense_category': '00000000-0000-0000-0000-000000000000',
    'description': 'Academia',
    'amount': '99.90',
    'type': 'recurring_expense',
    'date': '2026-03-05',
}

class ExpenseViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']

    def get_queryset(self):
        return Expense.objects.filter(expense_cycle__wallet__user=self.request.user).select_related(
            'expense_cycle',
            'expense_category',
            'installment_serie',
            'recurring_root',
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseCreateSerializer
        return ExpenseReadSerializer

    @swagger_auto_schema(
        operation_summary='List expenses by cycle',
        operation_description="Requires 'expense_cycle' query parameter.",
        manual_parameters=[
            openapi.Parameter(
                'expense_cycle',
                openapi.IN_QUERY,
                description='Expense cycle ID (UUID).',
                type=openapi.TYPE_STRING,
                format='uuid',
                required=True,
            ),
        ],
        tags=['Wallet Expenses'],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        cycle_id = request.query_params.get('expense_cycle')
        if not cycle_id:
            raise ValidationError({'expense_cycle': "The 'expense_cycle' query parameter is required."})
        queryset = queryset.filter(expense_cycle_id=cycle_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ExpenseReadSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ExpenseReadSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='Create expense',
        operation_description='Creates single or recurring expense. Installment expenses are created from installment series.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['expense_cycle', 'expense_category', 'description', 'amount', 'type', 'date'],
            properties={
                'expense_cycle': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                'expense_category': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, max_length=120),
                'amount': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['single_expense', 'recurring_expense', 'installment_expense'],
                ),
                'date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
            },
            examples={
                'single_expense': {'value': EXPENSE_CREATE_SINGLE_EXAMPLE},
                'recurring_expense': {'value': EXPENSE_CREATE_RECURRING_EXAMPLE},
            },
        ),
        responses={201: ExpenseReadSerializer},
        tags=['Wallet Expenses'],
    )
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return response

    def perform_create(self, serializer):
        expense = serializer.save()
        if expense.type == Expense.TYPE_RECURRING:
            sync_recurring_expense_to_existing_cycles(expense)
