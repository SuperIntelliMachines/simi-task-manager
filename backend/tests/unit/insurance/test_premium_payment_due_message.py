from app.services.insurance_service import (
    LIC_PREMIUM_PAYMENT_URL,
    PREMIUM_PAYMENT_DUE_TEMPLATE,
    build_premium_payment_due_message,
)


def test_build_premium_payment_due_message_replaces_placeholders():
    message = build_premium_payment_due_message(
        customer_name="John",
        policy_number="POL-2026-001",
        logged_in_user_name="Uday Kumar",
    )

    assert message.startswith("Dear John,\n\n")
    assert "Premium due for Policy No. POL-2026-001 has not yet been received." in message
    assert "Please pay your premium online:" in message
    assert LIC_PREMIUM_PAYMENT_URL in message
    assert "Kindly ignore this message if payment has already been made." in message
    assert message.endswith("Thank you,\nUday Kumar")
    assert "{customer_name}" not in message
    assert "{policy_number}" not in message
    assert "{logged_in_user_name}" not in message


def test_premium_payment_due_template_preserves_line_breaks():
    assert "Dear {customer_name},\n\n" in PREMIUM_PAYMENT_DUE_TEMPLATE
    assert f"Please pay your premium online:\n{LIC_PREMIUM_PAYMENT_URL}\n\n" in PREMIUM_PAYMENT_DUE_TEMPLATE
    assert "Thank you,\n{logged_in_user_name}" in PREMIUM_PAYMENT_DUE_TEMPLATE
