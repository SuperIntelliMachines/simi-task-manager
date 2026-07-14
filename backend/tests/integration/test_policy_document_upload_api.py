from collections.abc import AsyncGenerator
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db_session
from app.main import app


@pytest.fixture
async def insurance_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_policy_document_endpoint(tmp_path, monkeypatch, insurance_client):
    upload_dir = tmp_path / "policies"
    monkeypatch.setattr(
        "app.services.policy_document_service.DEFAULT_UPLOAD_DIR",
        upload_dir,
    )

    response = await insurance_client.post(
        "/api/v1/insurance/policies/upload-document",
        data={"policy_id": "25"},
        files={"file": ("policy.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_name"].startswith("policy_25_")
    assert body["document_name"].endswith(".pdf")
    assert body["document_path"] == f"/uploads/policies/{body['document_name']}"
    assert (upload_dir / body["document_name"]).exists()


@pytest.mark.asyncio
async def test_upload_policy_document_rejects_unsupported_file(insurance_client):
    response = await insurance_client.post(
        "/api/v1/insurance/policies/upload-document",
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
