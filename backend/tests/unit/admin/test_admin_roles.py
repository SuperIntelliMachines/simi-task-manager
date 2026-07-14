import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.enums import UserRole
from app.tests.utils.user import create_random_user
from app.tests.utils.utils import get_admin_token_headers

@pytest.mark.parametrize("role", [
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPPORT_ENGINEER,
    UserRole.IMPLEMENTATION_MANAGER,
])
def test_admin_access_granted(client: TestClient, db: Session, role):
    user = create_random_user(db, role=role)
    headers = get_admin_token_headers(client, user.email, "password")
    response = client.get("/api/v1/admin/customers", headers=headers)
    assert response.status_code == 200

def test_admin_access_denied(client: TestClient, db: Session):
    user = create_random_user(db, role=UserRole.TENANT_USER)
    headers = get_admin_token_headers(client, user.email, "password")
    response = client.get("/api/v1/admin/customers", headers=headers)
    assert response.status_code == 403