from django.contrib import admin

from .models import Expense, ExpenseCategory, ExpenseCycle, InstallmentSerie, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'user',
        'limit',
        'cycle_limit_default',
        'cycle_starts',
        'cycle_ends',
        'active',
        'created_at',
    )
    list_filter = ('active',)
    search_fields = ('name', 'user__username', 'user__email')
    autocomplete_fields = ('user',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'icon', 'color', 'user', 'created_at')
    search_fields = ('name', 'icon', 'color', 'user__username', 'user__email')
    autocomplete_fields = ('user',)


@admin.register(ExpenseCycle)
class ExpenseCycleAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'month', 'limit', 'start_date', 'end_date', 'created_at')
    search_fields = ('wallet__name', 'wallet__user__username')
    autocomplete_fields = ('wallet',)


@admin.register(InstallmentSerie)
class InstallmentSerieAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'description',
        'wallet',
        'expense_category',
        'total_amount',
        'installments_count',
        'start_date',
        'active',
        'created_at',
    )
    search_fields = ('description', 'wallet__name', 'wallet__user__username', 'expense_category__name')
    autocomplete_fields = ('wallet', 'expense_category')
    list_filter = ('active',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'description',
        'type',
        'amount',
        'date',
        'expense_cycle',
        'expense_category',
        'installment_serie',
        'created_at',
    )
    search_fields = (
        'description',
        'expense_cycle__wallet__name',
        'expense_cycle__wallet__user__username',
        'expense_category__name',
    )
    autocomplete_fields = ('expense_cycle', 'expense_category', 'installment_serie', 'recurring_root')
    list_filter = ('type',)
