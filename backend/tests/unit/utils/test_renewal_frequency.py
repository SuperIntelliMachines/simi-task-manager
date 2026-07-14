from app.utils.renewal_frequency import (
    RENEWAL_FREQUENCY_HALF_YEARLY,
    RENEWAL_FREQUENCY_MONTHLY,
    RENEWAL_FREQUENCY_QUARTERLY,
    RENEWAL_FREQUENCY_YEARLY,
    renewal_frequency_label,
    validate_renewal_frequency,
)
import pytest


def test_validate_renewal_frequency_accepts_allowed_values():
    assert validate_renewal_frequency("monthly") == RENEWAL_FREQUENCY_MONTHLY
    assert validate_renewal_frequency("Quarterly") == RENEWAL_FREQUENCY_QUARTERLY
    assert validate_renewal_frequency("half_yearly") == RENEWAL_FREQUENCY_HALF_YEARLY
    assert validate_renewal_frequency("Yearly") == RENEWAL_FREQUENCY_YEARLY


def test_validate_renewal_frequency_rejects_empty_and_invalid():
    with pytest.raises(ValueError, match="required"):
        validate_renewal_frequency("")
    with pytest.raises(ValueError, match="required"):
        validate_renewal_frequency(None)
    with pytest.raises(ValueError, match="invalid"):
        validate_renewal_frequency("weekly")


def test_renewal_frequency_label():
    assert renewal_frequency_label("half_yearly") == "Half-Yearly"
    assert renewal_frequency_label(None) == "Yearly"
    assert renewal_frequency_label("") == "Yearly"
    assert renewal_frequency_label("unknown") == "unknown"
