"""Tests for response model behavior independent of the tools."""

from conftest import document_json

from models import DocumentSummary


def test_web_url_uses_base_url_from_context() -> None:
    document = DocumentSummary.model_validate(
        document_json(id=42), context={"base_url": "http://paperless.test"}
    )
    assert document.web_url == "http://paperless.test/documents/42"


def test_web_url_absent_without_base_url_context() -> None:
    document = DocumentSummary.model_validate(document_json(id=42))
    assert document.web_url is None
