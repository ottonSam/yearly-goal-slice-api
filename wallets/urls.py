from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExpenseCategoryViewSet,
    ExpenseCycleViewSet,
    ExpenseViewSet,
    InstallmentSerieViewSet,
    WalletViewSet,
)


router = DefaultRouter()
router.register('wallets/cycle', ExpenseCycleViewSet, basename='wallet-expense-cycle')
router.register('wallets/categories', ExpenseCategoryViewSet, basename='wallet-expense-category')
router.register('wallets/installment-series', InstallmentSerieViewSet, basename='wallet-installment-serie')
router.register('wallets', WalletViewSet, basename='wallet')

expense_list_create_view = ExpenseViewSet.as_view({'get': 'list', 'post': 'create'})
expense_single_update_view = ExpenseViewSet.as_view({'patch': 'update_single'})
expense_cancel_recurring_view = ExpenseViewSet.as_view({'post': 'cancel_recurring'})

urlpatterns = [
    path('wallets/expenses/', expense_list_create_view, name='wallet-expense-list-create'),
    path('wallets/expenses/<uuid:pk>/', expense_single_update_view, name='wallet-expense-single-update'),
    path(
        'wallets/expenses/<uuid:pk>/cancel-recurring/',
        expense_cancel_recurring_view,
        name='wallet-expense-cancel-recurring',
    ),
]
urlpatterns += router.urls
