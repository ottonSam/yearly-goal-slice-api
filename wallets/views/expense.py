from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from wallets.models import Expense
from wallets.permissions import IsOwner
from wallets.serializers import ExpenseCreateSerializer, ExpenseReadSerializer, ExpenseSingleUpdateSerializer
from wallets.services.expense import cancel_recurring_from, sync_recurring_expense_to_existing_cycles


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

EXPENSE_SINGLE_UPDATE_EXAMPLE = {
    'expense_category': '00000000-0000-0000-0000-000000000000',
    'amount': '180.00',
    'description': 'Mercado mensal atualizado',
    'date': '2026-03-28',
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
        if self.action == 'update_single':
            return ExpenseSingleUpdateSerializer
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

    @swagger_auto_schema(
        operation_summary='Update single expense',
        operation_description=(
            "Partially updates a single expense. Only 'expense_category', 'amount', "
            "'description' and/or 'date' are allowed."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'expense_category': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                'amount': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, max_length=120),
                'date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
            },
            example=EXPENSE_SINGLE_UPDATE_EXAMPLE,
        ),
        responses={200: ExpenseReadSerializer},
        tags=['Wallet Expenses'],
    )
    def update_single(self, request, pk=None, *args, **kwargs):
        expense = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer(expense, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ExpenseReadSerializer(expense).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='Cancel recurring expense series',
        operation_description='Deletes the recurring expense root (past cycle) and all recurring expenses from that cycle onward.',
        request_body=None,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                    'deleted_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                },
            )
        },
        tags=['Wallet Expenses'],
    )
    def cancel_recurring(self, request, pk=None, *args, **kwargs):
        expense = get_object_or_404(self.get_queryset(), pk=pk)
        if expense.type != Expense.TYPE_RECURRING:
            raise ValidationError({'detail': "Only recurring expenses can be canceled."})

        root = expense if expense.recurring_root_id is None else expense.recurring_root
        deleted_count = cancel_recurring_from(root)
        return Response(
            {
                'detail': 'Recurring expense series canceled successfully.',
                'deleted_count': deleted_count,
            },
            status=status.HTTP_200_OK,
        )
