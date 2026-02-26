from django.contrib import admin

from .models import Wallet


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
