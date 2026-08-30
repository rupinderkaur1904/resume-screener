"""Unit tests for app/services/pdf_parser.py's pure validation/naming helpers."""
import pytest

from app.services.pdf_parser import make_safe_filename, validate_upload


def test_validate_upload_accepts_pdf_within_size_limit():
    validate_upload(filename="resume.pdf", file_size_bytes=1024)  # should not raise


def test_validate_upload_rejects_non_pdf_extension():
    with pytest.raises(ValueError):
        validate_upload(filename="resume.docx", file_size_bytes=1024)


def test_validate_upload_rejects_oversized_file():
    ten_mb = 10 * 1024 * 1024
    with pytest.raises(ValueError):
        validate_upload(filename="resume.pdf", file_size_bytes=ten_mb)


def test_make_safe_filename_replaces_spaces():
    result = make_safe_filename(user_id=1, original_filename="My Resume Final.pdf")
    assert " " not in result
    assert result.endswith(".pdf")
    assert result.startswith("1_")


def test_make_safe_filename_is_unique_across_calls():
    first = make_safe_filename(user_id=1, original_filename="resume.pdf")
    second = make_safe_filename(user_id=1, original_filename="resume.pdf")
    assert first != second
