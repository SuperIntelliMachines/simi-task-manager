import pytest

from app.utils.policy_email import validate_policy_email


def test_validate_policy_email_allows_none_and_blank():
    assert validate_policy_email(None) is None
    assert validate_policy_email("") is None
    assert validate_policy_email("   ") is None


def test_validate_policy_email_normalizes_valid_values():
    assert validate_policy_email("User@Example.com") == "user@example.com"
    assert validate_policy_email(" holder@domain.co.in ") == "holder@domain.co.in"


@pytest.mark.parametrize(
    "value",
    [
        "not-an-email",
        "missing@domain",
        "@example.com",
    ],
)
def test_validate_policy_email_rejects_invalid_values(value: str):
    with pytest.raises(ValueError, match="valid email address"):
        validate_policy_email(value)
