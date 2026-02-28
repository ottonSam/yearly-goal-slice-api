from django.db.models import Count
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from wallets.models import InstallmentSerie
from wallets.permissions import IsOwner
from wallets.serializers import InstallmentSerieCreateUpdateSerializer, InstallmentSerieReadSerializer
from wallets.services.expense import regenerate_installment_expenses


INSTALLMENT_SERIE_CREATE_EXAMPLE = {
    'wallet': '00000000-0000-0000-0000-000000000000',
    'expense_category': '00000000-0000-0000-0000-000000000000',
    'description': 'Notebook',
    'total_amount': '2400.00',
    'installments_count': 12,
    'start_date': '2026-03-10',
}


class InstallmentSerieViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    http_method_names = ['post', 'put', 'delete']
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return (
            InstallmentSerie.objects.filter(wallet__user=self.request.user)
            .annotate(expenses_count=Count('expenses'))
            .select_related('wallet', 'expense_category')
        )

    def get_serializer_class(self):
        return InstallmentSerieCreateUpdateSerializer

    @swagger_auto_schema(
        operation_summary='Create installment series',
        operation_description='Creates installment series and generates installment expenses in required cycles.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                'wallet',
                'expense_category',
                'description',
                'total_amount',
                'installments_count',
                'start_date',
            ],
            properties={
                'wallet': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                'expense_category': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, max_length=120),
                'total_amount': openapi.Schema(type=openapi.TYPE_STRING, description='Decimal with 2 fraction digits'),
                'installments_count': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1),
                'start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
            },
            example=INSTALLMENT_SERIE_CREATE_EXAMPLE,
        ),
        responses={201: InstallmentSerieReadSerializer},
        tags=['Wallet Installment Series'],
    )
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return response

    def perform_create(self, serializer):
        serie = serializer.save()
        regenerate_installment_expenses(serie)

    def perform_update(self, serializer):
        serie = serializer.save()
        regenerate_installment_expenses(serie)

    @swagger_auto_schema(
        operation_summary='Replace installment series',
        responses={200: InstallmentSerieReadSerializer},
        tags=['Wallet Installment Series'],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(InstallmentSerieReadSerializer(instance).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='Delete installment series',
        operation_description='Deletes installment series and related generated expenses.',
        request_body=None,
        tags=['Wallet Installment Series'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
