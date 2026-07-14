from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.policy_document_service import (
    PolicyDocumentUploadError,
    build_unique_filename,
    save_policy_document,
    validate_upload_file,
)


def _upload_file(
    *,
    filename: str,
    content: bytes = b"%PDF-1.4 test",
    content_type: str | None = "application/pdf",
) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type or ""})


@pytest.mark.asyncio
async def test_save_policy_document_writes_file_with_unique_name(tmp_path: Path):
    upload_dir = tmp_path / "policies"
    file = _upload_file(filename="scan.pdf")

    result = await save_policy_document(file, policy_id=25, upload_dir=upload_dir)

    assert result["document_name"].startswith("policy_25_")
    assert result["document_name"].endswith(".pdf")
    assert result["document_path"] == f"/uploads/policies/{result['document_name']}"
    assert (upload_dir / result["document_name"]).read_bytes() == b"%PDF-1.4 test"


@pytest.mark.asyncio
async def test_save_policy_document_avoids_filename_collision(tmp_path: Path):
    upload_dir = tmp_path / "policies"
    upload_dir.mkdir(parents=True)
    first_name = build_unique_filename(policy_id=25, extension="pdf", upload_dir=upload_dir)
    (upload_dir / first_name).write_bytes(b"existing")

    file = _upload_file(filename="scan.pdf")
    result = await save_policy_document(file, policy_id=25, upload_dir=upload_dir)

    assert result["document_name"] != first_name
    assert result["document_name"].startswith("policy_25_")
    assert (upload_dir / result["document_name"]).exists()


@pytest.mark.asyncio
async def test_save_policy_document_accepts_png_and_jpeg(tmp_path: Path):
    upload_dir = tmp_path / "policies"

    png = _upload_file(filename="photo.png", content=b"\x89PNG", content_type="image/png")
    png_result = await save_policy_document(png, policy_id=3, upload_dir=upload_dir)
    assert png_result["document_name"].endswith(".png")

    jpeg = _upload_file(filename="photo.jpeg", content=b"\xff\xd8\xff", content_type="image/jpeg")
    jpeg_result = await save_policy_document(jpeg, policy_id=3, upload_dir=upload_dir)
    assert jpeg_result["document_name"].endswith(".jpg")


@pytest.mark.asyncio
async def test_save_policy_document_rejects_unsupported_type(tmp_path: Path):
    file = _upload_file(filename="notes.txt", content=b"hello", content_type="text/plain")

    with pytest.raises(PolicyDocumentUploadError, match="Unsupported file type"):
        await save_policy_document(file, upload_dir=tmp_path / "policies")


@pytest.mark.asyncio
async def test_save_policy_document_rejects_empty_file(tmp_path: Path):
    file = _upload_file(filename="empty.pdf", content=b"", content_type="application/pdf")

    with pytest.raises(PolicyDocumentUploadError, match="empty"):
        await save_policy_document(file, upload_dir=tmp_path / "policies")


def test_validate_upload_file_requires_filename():
    file = UploadFile(filename="", file=BytesIO(b"x"))

    with pytest.raises(PolicyDocumentUploadError, match="file must be provided"):
        validate_upload_file(file)


def test_build_unique_filename_uses_policy_and_date(tmp_path: Path):
    name = build_unique_filename(policy_id=25, extension="pdf", upload_dir=tmp_path)
    assert name.startswith("policy_25_")
    assert name.endswith(".pdf")
