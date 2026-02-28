from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.utils import timezone

from wallets.models import Expense, ExpenseCycle


ZERO = Decimal('0.00')
CENT = Decimal('0.01')


@dataclass(frozen=True)
class CategorySpendingSnapshot:
    category_id: str
    category_name: str
    category_icon: str
    category_color: str
    total_spent: Decimal


@dataclass(frozen=True)
class ExpenseCycleBillingSnapshot:
    total_cycle_spent: Decimal
    spending_by_category: list[CategorySpendingSnapshot]
    total_cycle_installment_spent: Decimal
    total_cycle_recurring_spent: Decimal
    total_future_installment_spent: Decimal
    remaining_limit_per_day: Decimal | None


def _sum_amount(queryset) -> Decimal:
    total = queryset.aggregate(total=Sum('amount'))['total']
    return total if total is not None else ZERO


def _compute_remaining_limit_per_day(
    cycle: ExpenseCycle,
    total_cycle_spent: Decimal,
    reference_date: date,
) -> Decimal | None:
    if reference_date < cycle.start_date or reference_date > cycle.end_date:
        return None

    days_remaining = (cycle.end_date - reference_date).days + 1
    if days_remaining <= 0:
        return None

    remaining_limit = cycle.limit - total_cycle_spent
    remaining_per_day = (remaining_limit / Decimal(days_remaining)).quantize(CENT, rounding=ROUND_HALF_UP)
    return remaining_per_day if remaining_per_day > ZERO else ZERO


def build_expense_cycle_billing_snapshot(
    cycle: ExpenseCycle,
    reference_date: date | None = None,
) -> ExpenseCycleBillingSnapshot:
    if reference_date is None:
        reference_date = timezone.localdate()

    cycle_expenses = Expense.objects.filter(expense_cycle=cycle)
    spending_by_category = [
        CategorySpendingSnapshot(
            category_id=item['expense_category_id'],
            category_name=item['expense_category__name'],
            category_icon=item['expense_category__icon'],
            category_color=item['expense_category__color'],
            total_spent=item['total_spent'],
        )
        for item in (
            cycle_expenses.values(
                'expense_category_id',
                'expense_category__name',
                'expense_category__icon',
                'expense_category__color',
            )
            .annotate(total_spent=Sum('amount'))
            .order_by('-total_spent', 'expense_category__name')
        )
    ]

    total_cycle_spent = _sum_amount(cycle_expenses)
    total_cycle_installment_spent = _sum_amount(cycle_expenses.filter(type=Expense.TYPE_INSTALLMENT))
    total_cycle_recurring_spent = _sum_amount(cycle_expenses.filter(type=Expense.TYPE_RECURRING))
    total_future_installment_spent = _sum_amount(
        Expense.objects.filter(
            expense_cycle__wallet=cycle.wallet,
            expense_cycle__month__gt=cycle.month,
            type=Expense.TYPE_INSTALLMENT,
        )
    )

    return ExpenseCycleBillingSnapshot(
        total_cycle_spent=total_cycle_spent,
        spending_by_category=spending_by_category,
        total_cycle_installment_spent=total_cycle_installment_spent,
        total_cycle_recurring_spent=total_cycle_recurring_spent,
        total_future_installment_spent=total_future_installment_spent,
        remaining_limit_per_day=_compute_remaining_limit_per_day(
            cycle=cycle,
            total_cycle_spent=total_cycle_spent,
            reference_date=reference_date,
        ),
    )
