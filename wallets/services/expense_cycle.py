from calendar import monthrange
from datetime import date


def _clamped_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + delta
    new_year, new_month_index = divmod(month_index, 12)
    return new_year, new_month_index + 1


def compute_cycle_for_date(cycle_starts: int, cycle_ends: int, input_date: date) -> tuple[date, date, date]:
    candidate_start = _clamped_date(input_date.year, input_date.month, cycle_starts)
    if input_date < candidate_start:
        prev_year, prev_month = _shift_month(input_date.year, input_date.month, -1)
        start_date = _clamped_date(prev_year, prev_month, cycle_starts)
    else:
        start_date = candidate_start

    if cycle_ends >= cycle_starts:
        end_year, end_month = start_date.year, start_date.month
    else:
        end_year, end_month = _shift_month(start_date.year, start_date.month, 1)

    end_date = _clamped_date(end_year, end_month, cycle_ends)
    month = date(start_date.year, start_date.month, 1)
    return month, start_date, end_date


def compute_cycle_for_month(cycle_starts: int, cycle_ends: int, month_date: date) -> tuple[date, date, date]:
    start_date = _clamped_date(month_date.year, month_date.month, cycle_starts)

    if cycle_ends >= cycle_starts:
        end_year, end_month = start_date.year, start_date.month
    else:
        end_year, end_month = _shift_month(start_date.year, start_date.month, 1)

    end_date = _clamped_date(end_year, end_month, cycle_ends)
    month = date(start_date.year, start_date.month, 1)
    return month, start_date, end_date
