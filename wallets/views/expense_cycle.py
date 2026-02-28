from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from wallets.models import ExpenseCycle, Wallet
from wallets.permissions import IsOwner
from wallets.serializers import (
    ExpenseCycleDetailSerializer,
    ExpenseCycleReadSerializer,
    ExpenseCycleResolveSerializer,
    ExpenseCycleUpdateSerializer,
)
from wallets.services.expense_cycle import compute_cycle_for_date, compute_cycle_for_month
from wallets.services.expense import materialize_recurring_expenses_for_cycle


EXPENSE_CYCLE_RESOLVE_BY_DATE_EXAMPLE = {
    'wallet': '00000000-0000-0000-0000-000000000000',
    'date': '2026-02-26',
}

EXPENSE_CYCLE_RESOLVE_BY_MONTH_EXAMPLE = {
    'wallet': '00000000-0000-0000-0000-000000000000',
    'month': '2026-02',
}

EXPENSE_CYCLE_UPDATE_EXAMPLE = {
    'limit': '1500.00',
}


@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        operation_summary='Retrieve expense cycle',
        responses={200: ExpenseCycleDetailSerializer},
        tags=['Wallet Expense Cycles'],
    ),
)
class ExpenseCycleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['month', 'created_at']
    ordering = ['-month']
    search_fields = ['month']

    def get_queryset(self):
        queryset = ExpenseCycle.objects.filter(wallet__user=self.request.user).select_related('wallet')
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('expenses')
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExpenseCycleDetailSerializer
        if self.action == 'resolve':
            return ExpenseCycleResolveSerializer
        if self.action in {'update', 'partial_update'}:
            return ExpenseCycleUpdateSerializer
        return ExpenseCycleReadSerializer

    @swagger_auto_schema(
        operation_summary='Resolve expense cycle by date or month',
        operation_description='Returns the cycle for the given date/month. Creates it when missing.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['wallet'],
            properties={
                'wallet': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                'date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                'month': openapi.Schema(type=openapi.TYPE_STRING, description='YYYY-MM or YYYY-MM-01'),
            },
            examples={
                'resolve_by_date': {'value': EXPENSE_CYCLE_RESOLVE_BY_DATE_EXAMPLE},
                'resolve_by_month': {'value': EXPENSE_CYCLE_RESOLVE_BY_MONTH_EXAMPLE},
            },
        ),
        responses={200: ExpenseCycleReadSerializer, 201: ExpenseCycleReadSerializer},
        tags=['Wallet Expense Cycles'],
    )
    @action(detail=False, methods=['post'], url_path='resolve')
    def resolve(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = self._get_user_wallet(serializer.validated_data['wallet'])
        input_date = serializer.validated_data.get('date')
        month_value = serializer.validated_data.get('month')

        if input_date is not None:
            month, start_date, end_date = compute_cycle_for_date(
                wallet.cycle_starts,
                wallet.cycle_ends,
                input_date,
            )
        else:
            month, start_date, end_date = compute_cycle_for_month(
                wallet.cycle_starts,
                wallet.cycle_ends,
                month_value,
            )

        cycle, created = ExpenseCycle.objects.get_or_create(
            wallet=wallet,
            month=month,
            defaults={
                'limit': wallet.cycle_limit_default,
                'start_date': start_date,
                'end_date': end_date,
            },
        )
        materialize_recurring_expenses_for_cycle(cycle)

        response_data = {
            'created': created,
            'cycle': ExpenseCycleReadSerializer(cycle).data,
        }
        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary='Update cycle limit',
        operation_description="Only the 'limit' field can be updated.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['limit'],
            properties={
                'limit': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
            },
            example=EXPENSE_CYCLE_UPDATE_EXAMPLE,
        ),
        responses={200: ExpenseCycleReadSerializer},
        tags=['Wallet Expense Cycles'],
    )
    def partial_update(self, request, *args, **kwargs):
        return self._update_limit_only(request, partial=True, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Replace cycle limit',
        operation_description="Only the 'limit' field can be updated.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['limit'],
            properties={
                'limit': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
            },
            example=EXPENSE_CYCLE_UPDATE_EXAMPLE,
        ),
        responses={200: ExpenseCycleReadSerializer},
        tags=['Wallet Expense Cycles'],
    )
    def update(self, request, *args, **kwargs):
        return self._update_limit_only(request, partial=False, *args, **kwargs)

    def _update_limit_only(self, request, partial: bool, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ExpenseCycleReadSerializer(instance).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='List expense cycles',
        tags=['Wallet Expense Cycles'],
    )
    def list(self, request, *args, **kwargs):
        wallet_id = request.query_params.get('wallet')
        if not wallet_id:
            raise ValidationError({'wallet': "The 'wallet' query parameter is required."})

        wallet = self._get_user_wallet(wallet_id)
        queryset = self.filter_queryset(self.get_queryset().filter(wallet=wallet))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ExpenseCycleReadSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ExpenseCycleReadSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _get_user_wallet(self, wallet_id):
        return get_object_or_404(
            Wallet.objects.filter(
                id=wallet_id,
                user=self.request.user,
                active=True,
            )
        )
