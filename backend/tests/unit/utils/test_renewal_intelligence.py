from datetime import timedelta

from app.utils.datetime_utils import utcnow_naive
from app.utils.renewal_intelligence import (
    RENEWAL_STATUS_DUE_SOON,
    RENEWAL_STATUS_EXPIRED,
    RENEWAL_STATUS_EXPIRED_OVER_90,
    RENEWAL_STATUS_FUTURE,
    RENEWAL_STATUS_PAID_RENEWED,
    classify_renewal_intelligence_status,
    is_in_renewal_intelligence_chart_window,
)


class _Policy:
    def __init__(self, *, status: str, expiry_date, premium: int = 10000):
        self.status = status
        self.expiry_date = expiry_date
        self.premium = premium


def test_classify_renewal_intelligence_status():
    now = utcnow_naive()

    assert classify_renewal_intelligence_status(_Policy(status="renewed", expiry_date=now + timedelta(days=120))) == RENEWAL_STATUS_PAID_RENEWED
    assert classify_renewal_intelligence_status(_Policy(status="active", expiry_date=now - timedelta(days=120))) == RENEWAL_STATUS_EXPIRED_OVER_90
    assert classify_renewal_intelligence_status(_Policy(status="active", expiry_date=now - timedelta(days=10))) == RENEWAL_STATUS_EXPIRED
    assert classify_renewal_intelligence_status(_Policy(status="active", expiry_date=now + timedelta(days=5))) == RENEWAL_STATUS_DUE_SOON
    assert classify_renewal_intelligence_status(_Policy(status="active", expiry_date=now + timedelta(days=30))) == RENEWAL_STATUS_FUTURE


def test_is_in_renewal_intelligence_chart_window():
    assert is_in_renewal_intelligence_chart_window(30) is True
    assert is_in_renewal_intelligence_chart_window(0) is True
    assert is_in_renewal_intelligence_chart_window(-90) is True
    assert is_in_renewal_intelligence_chart_window(31) is False
    assert is_in_renewal_intelligence_chart_window(-91) is False
    assert is_in_renewal_intelligence_chart_window(None) is False
