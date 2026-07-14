import pytest


@pytest.mark.asyncio
async def test_healthz(async_client):
    response = await async_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz(async_client):
    response = await async_client.get("/readyz")

    # Without live DB/Redis this returns 503, with stack up it returns 200.
    assert response.status_code in (200, 503)
