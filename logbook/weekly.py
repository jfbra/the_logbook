import datetime

from django.db.models import Sum
from django.utils import timezone

from .models import Session


def week_start(day: datetime.date) -> datetime.date:
    """The Monday of the week containing `day`."""
    return day - datetime.timedelta(days=day.weekday())


def _total_minutes(start: datetime.date, end: datetime.date) -> int:
    """Total duration of Sessions dated in [start, end); no duration counts as zero."""
    total = Session.objects.filter(date__gte=start, date__lt=end).aggregate(
        total=Sum("duration_minutes")
    )["total"]
    return total or 0


def weekly_totals() -> tuple[int, int]:
    """(this week, last week) total minutes; weeks run Monday-Sunday, local time."""
    this_monday = week_start(timezone.localdate())
    last_monday = this_monday - datetime.timedelta(days=7)
    next_monday = this_monday + datetime.timedelta(days=7)
    return _total_minutes(this_monday, next_monday), _total_minutes(
        last_monday, this_monday
    )
