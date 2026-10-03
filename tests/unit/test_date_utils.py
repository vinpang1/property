from datetime import date

from src.ingestion.date_utils import month_cutoff


def test_month_cutoff_returns_first_day_of_month():
    cutoff = month_cutoff(6)
    assert cutoff.day == 1
    assert isinstance(cutoff, date)
