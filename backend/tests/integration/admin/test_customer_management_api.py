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

def test_list_customers(admin_client):
    client, headers = admin_client
    response = client.get(f"{settings.API_V1_STR}/admin/customers", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_customer(admin_client):
    client, headers = admin_client
    data = {"name": "Test Customer", "industry": "Insurance"}
    response = client.post(f"{settings.API_V1_STR}/admin/customers", json=data, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Test Customer"

def test_get_customer(admin_client):
    client, headers = admin_client
    customer_id = 1  # Replace with actual ID from setup
    response = client.get(f"{settings.API_V1_STR}/admin/customers/{customer_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == customer_id

def test_update_customer(admin_client):
    client, headers = admin_client
    customer_id = 1  # Replace with actual ID from setup
    data = {"name": "Updated Customer"}
    response = client.patch(f"{settings.API_V1_STR}/admin/customers/{customer_id}", json=data, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Customer"