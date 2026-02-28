from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from wallets.models import Expense, Wallet
from wallets.services.expense import resolve_or_create_cycle_for_date


ZERO = Decimal('0.00')


@dataclass(frozen=True)
class WalletLimitSnapshot:
    remaining_total_limit: Decimal
    remaining_cycle_limit: Decimal


def _sum_amount(queryset) -> Decimal:
    total = queryset.aggregate(total=Sum('amount'))['total']
    return total if total is not None else ZERO


def compute_wallet_remaining_limits(wallet: Wallet, reference_date: date) -> WalletLimitSnapshot:
    current_cycle = resolve_or_create_cycle_for_date(wallet=wallet, target_date=reference_date)

    current_cycle_spent = _sum_amount(Expense.objects.filter(expense_cycle=current_cycle))
    future_cycles_spent = _sum_amount(
        Expense.objects.filter(
            expense_cycle__wallet=wallet,
            expense_cycle__month__gt=current_cycle.month,
            type__in=(Expense.TYPE_SINGLE, Expense.TYPE_INSTALLMENT),
        )
    )

    return WalletLimitSnapshot(
        remaining_total_limit=wallet.limit - current_cycle_spent - future_cycles_spent,
        remaining_cycle_limit=current_cycle.limit - current_cycle_spent,
    )
