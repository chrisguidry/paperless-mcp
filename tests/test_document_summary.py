"""Tests for response model behavior independent of the tools."""

import pytest
from conftest import document_json
from pydantic import ValidationError

from paperless_mcp.documents import DocumentSummary


def test_web_url_uses_base_url_from_context() -> None:
    document = DocumentSummary.model_validate(
        document_json(id=42), context={"base_url": "http://paperless.test"}
    )
    assert document.web_url == "http://paperless.test/documents/42"


def test_web_url_absent_without_base_url_context() -> None:
    document = DocumentSummary.model_validate(document_json(id=42))
    assert document.web_url is None


def test_non_object_fails_as_not_a_document() -> None:
    with pytest.raises(ValidationError, match="valid dictionary"):
        DocumentSummary.model_validate(
            42, context={"base_url": "http://paperless.test"}
        )
