"""Store uploaded insurance policy documents on the local filesystem."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_UPLOAD_DIR = PROJECT_ROOT / "uploads" / "policies"
PUBLIC_UPLOAD_PREFIX = "/uploads/policies"

ALLOWED_EXTENSIONS = frozenset({"pdf", "jpg", "jpeg", "png"})
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
)

_EXTENSION_BY_CONTENT_TYPE = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}


class PolicyDocumentUploadError(ValueError):
    """Raised when an uploaded policy document fails validation."""


def resolve_upload_dir(upload_dir: Path | None = None) -> Path:
    directory = upload_dir or DEFAULT_UPLOAD_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _normalize_extension(filename: str | None, content_type: str | None) -> str:
    extension = ""
    if filename and "." in filename:
        extension = filename.rsplit(".", 1)[-1].strip().lower()

    if extension in ALLOWED_EXTENSIONS:
        if extension == "jpeg":
            return "jpg"
        return extension

    if content_type:
        normalized_type = content_type.split(";", 1)[0].strip().lower()
        mapped = _EXTENSION_BY_CONTENT_TYPE.get(normalized_type)
        if mapped:
            return mapped

    raise PolicyDocumentUploadError(
        "Unsupported file type. Allowed types: PDF, JPG, JPEG, PNG."
    )


def _sanitize_policy_id(policy_id: int | None) -> int:
    if policy_id is None:
        return 0
    if policy_id < 0:
        raise PolicyDocumentUploadError("policy_id must be zero or a positive integer.")
    return policy_id


def build_unique_filename(*, policy_id: int, extension: str, upload_dir: Path) -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    base = f"policy_{policy_id}_{date_part}"
    candidate = f"{base}.{extension}"
    counter = 1
    while (upload_dir / candidate).exists():
        candidate = f"{base}_{counter}.{extension}"
        counter += 1
    return candidate


def validate_upload_file(file: UploadFile) -> None:
    if not file.filename:
        raise PolicyDocumentUploadError("A file must be provided.")

    try:
        _normalize_extension(file.filename, file.content_type)
    except PolicyDocumentUploadError:
        raise


async def save_policy_document(
    file: UploadFile,
    *,
    policy_id: int | None = None,
    upload_dir: Path | None = None,
) -> dict[str, str]:
    """Validate and persist an uploaded policy document."""
    validate_upload_file(file)

    directory = resolve_upload_dir(upload_dir)
    safe_policy_id = _sanitize_policy_id(policy_id)
    extension = _normalize_extension(file.filename, file.content_type)
    document_name = build_unique_filename(
        policy_id=safe_policy_id,
        extension=extension,
        upload_dir=directory,
    )

    content = await file.read()
    if not content:
        raise PolicyDocumentUploadError("Uploaded file is empty.")

    destination = directory / document_name
    destination.write_bytes(content)

    return {
        "document_name": document_name,
        "document_path": f"{PUBLIC_UPLOAD_PREFIX}/{document_name}",
    }


def is_safe_document_filename(filename: str) -> bool:
    """Guard against path traversal in stored filenames."""
    return bool(re.fullmatch(r"policy_\d+_\d{8}(?:_\d+)?\.(?:pdf|jpg|png)", filename))
