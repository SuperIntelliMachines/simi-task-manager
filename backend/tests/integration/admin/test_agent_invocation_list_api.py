import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.config import settings
from tests.utils.user import create_random_user
from tests.utils.utils import get_admin_token_headers

@pytest.fixture(scope="module")
def admin_client(client: TestClient, db: Session):
    user = create_random_user(db, is_admin=True)
    token_headers = get_admin_token_headers(client, user.email, "password")
    return client, token_headers

def test_get_agent_invocation_list(admin_client):
    client, headers = admin_client
    organization_id = 1  # Replace with actual organization ID from setup
    response = client.get(f"{settings.API_V1_STR}/admin/customers/{organization_id}/agent-invocations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "invocations" in data
    assert isinstance(data["invocations"], list)