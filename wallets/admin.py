from django.contrib import admin

from .models import ExpenseCategory, ExpenseCycle, Wallet


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
