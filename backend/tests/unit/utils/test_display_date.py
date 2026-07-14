import pytest
from datetime import datetime

from app.utils.display_date import parse_display_date, validate_expiry_datetime


def test_parse_display_date_accepts_valid_dates():
    parsed = parse_display_date("15-06-2026")
    assert parsed == datetime(2026, 6, 15, 12, 0, 0)

    parsed = parse_display_date("01-01-2027")
    assert parsed == datetime(2027, 1, 1, 12, 0, 0)


@pytest.mark.parametrize(
    "value",
    [
        "01-01-222222",
        "15-06-20266",
        "01-01-2026123",
        "13-06-yyyy",
        "31-02-2026",
        "15/06/2026",
    ],
)
def test_parse_display_date_rejects_invalid_values(value: str):
    with pytest.raises(ValueError):
        parse_display_date(value)


def test_validate_expiry_datetime_rejects_out_of_range_years():
    with pytest.raises(ValueError):
        validate_expiry_datetime(datetime(1800, 1, 1, 12, 0, 0))

    with pytest.raises(ValueError):
        validate_expiry_datetime(datetime(3000, 1, 1, 12, 0, 0))

    normalized = validate_expiry_datetime(datetime(2026, 6, 15, 12, 0, 0))
    assert normalized.year == 2026
