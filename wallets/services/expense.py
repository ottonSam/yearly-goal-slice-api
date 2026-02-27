from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_DOWN

from django.db.models import Q

from wallets.models import Expense, ExpenseCycle, InstallmentSerie, Wallet
from wallets.services.expense_cycle import compute_cycle_for_date


CENT = Decimal('0.01')


def _clamped_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + delta
    new_year, new_month_index = divmod(month_index, 12)
    return new_year, new_month_index + 1


def _add_months(base_date: date, months_to_add: int) -> date:
    year, month = _shift_month(base_date.year, base_date.month, months_to_add)
    return _clamped_date(year, month, base_date.day)


def _split_installment_amounts(total_amount: Decimal, installments_count: int) -> list[Decimal]:
    base_amount = (total_amount / installments_count).quantize(CENT, rounding=ROUND_DOWN)
    amounts = [base_amount for _ in range(installments_count)]
    remainder = (total_amount - (base_amount * installments_count)).quantize(CENT)

    index = 0
    while remainder > 0:
        amounts[index] += CENT
        remainder -= CENT
        index += 1
        if index == installments_count:
            index = 0

    return amounts


def resolve_or_create_cycle_for_date(wallet: Wallet, target_date: date) -> ExpenseCycle:
    month, start_date, end_date = compute_cycle_for_date(
        wallet.cycle_starts,
        wallet.cycle_ends,
        target_date,
    )
    cycle, _ = ExpenseCycle.objects.get_or_create(
        wallet=wallet,
        month=month,
        defaults={
            'limit': wallet.cycle_limit_default,
            'start_date': start_date,
            'end_date': end_date,
        },
    )
    return cycle


def regenerate_installment_expenses(installment_serie: InstallmentSerie) -> list[Expense]:
    installment_serie.expenses.all().delete()

    amounts = _split_installment_amounts(
        total_amount=installment_serie.total_amount,
        installments_count=installment_serie.installments_count,
    )
    created: list[Expense] = []

    for index in range(installment_serie.installments_count):
        expense_date = _add_months(installment_serie.start_date, index)
        cycle = resolve_or_create_cycle_for_date(installment_serie.wallet, expense_date)
        created.append(
            Expense.objects.create(
                expense_cycle=cycle,
                expense_category=installment_serie.expense_category,
                installment_serie=installment_serie,
                description=installment_serie.description,
                amount=amounts[index],
                type=Expense.TYPE_INSTALLMENT,
                date=expense_date,
            )
        )

    return created


def _materialize_recurring_root_on_cycle(root: Expense, cycle: ExpenseCycle) -> None:
    if root.expense_cycle_id == cycle.id:
        return

    if root.recurring_canceled_from is not None and cycle.month >= root.recurring_canceled_from:
        return

    if Expense.objects.filter(expense_cycle=cycle, recurring_root=root).exists():
        return

    recurring_date = _clamped_date(cycle.month.year, cycle.month.month, root.date.day)
    Expense.objects.create(
        expense_cycle=cycle,
        expense_category=root.expense_category,
        recurring_root=root,
        description=root.description,
        amount=root.amount,
        type=Expense.TYPE_RECURRING,
        date=recurring_date,
    )


def materialize_recurring_expenses_for_cycle(cycle: ExpenseCycle) -> None:
    roots = Expense.objects.filter(
        type=Expense.TYPE_RECURRING,
        recurring_root__isnull=True,
        expense_cycle__wallet=cycle.wallet,
        expense_cycle__month__lte=cycle.month,
    ).select_related('expense_cycle', 'expense_category')

    for root in roots:
        _materialize_recurring_root_on_cycle(root, cycle)


def sync_recurring_expense_to_existing_cycles(root: Expense) -> None:
    cycles = ExpenseCycle.objects.filter(
        wallet=root.expense_cycle.wallet,
        month__gt=root.expense_cycle.month,
    ).order_by('month')
    for cycle in cycles:
        _materialize_recurring_root_on_cycle(root, cycle)


def cancel_recurring_from(expense: Expense) -> int:
    root = expense if expense.recurring_root_id is None else expense.recurring_root
    cancel_from_month = expense.expense_cycle.month

    if root.expense_cycle.month < cancel_from_month:
        root.recurring_canceled_from = cancel_from_month
        root.save(update_fields=['recurring_canceled_from', 'updated_at'])

    deleted, _ = Expense.objects.filter(
        Q(id=root.id) | Q(recurring_root=root),
        expense_cycle__month__gte=cancel_from_month,
    ).delete()
    return deleted
