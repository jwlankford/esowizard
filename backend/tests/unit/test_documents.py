import json

import pytest
from pydantic import ValidationError

from app.core.categories import ESOCategory
from app.schemas.knowledge import ImportDocument
from app.services.knowledge.ingestion import DocumentLoadError, load_documents
from app.services.knowledge.normalizer import (
    compute_content_hash,
    normalize_document,
    normalize_text,
    slugify,
)

VALID = {
    "title": "SYNTHETIC Test Document",
    "category": "CRAFTING",
    "source": {"name": "Synthetic Source", "url": "https://example.com"},
    "content": "Synthetic content.",
}


def test_valid_document_and_metadata():
    document = ImportDocument.model_validate({**VALID, "metadata": {"patch": "synthetic"}})
    assert document.category is ESOCategory.CRAFTING
    assert document.source.url == "https://example.com/"
    assert document.metadata == {"patch": "synthetic"}


@pytest.mark.parametrize(
    "change",
    [
        {"category": "NOT_A_CATEGORY"},
        {"category": "Items"},
        {"title": ""},
        {"content": "   "},
        {"source": {"name": "x", "url": "javascript:alert(1)"}},
        {"source": {"name": "x", "url": "ftp://example.com"}},
        {"canonical_url": "not a url"},
        {"unknown_field": 1},
        {"metadata": {"bad": {1, 2}}},
        {"metadata": {"big": "x" * 30_000}},
    ],
)
def test_invalid_documents_are_rejected(change):
    with pytest.raises(ValidationError):
        ImportDocument.model_validate({**VALID, **change})


def test_every_category_is_unique_and_labelled():
    values = [category.value for category in ESOCategory]
    assert len(values) == len(set(values)) == 21
    assert ESOCategory.PVP.label == "PvP"
    assert ESOCategory.GEAR_SET.label == "Gear Set"


def test_normalization_and_hash_are_deterministic():
    messy = ImportDocument.model_validate(
        {**VALID, "content": "Line one  \r\n\r\n\r\n\r\nLine\u00a0two\r\n"}
    )
    clean = ImportDocument.model_validate({**VALID, "content": "Line one\n\nLine two"})
    first, second = normalize_document(messy), normalize_document(clean)
    assert first.content == "Line one\n\nLine two"
    assert first.content_hash == second.content_hash
    assert first.slug == "synthetic-test-document"
    assert first.external_id == first.slug
    assert len(first.content_hash) == 64


def test_hash_changes_with_title_category_or_content():
    base = compute_content_hash("T", "ITEM", "body")
    assert base == compute_content_hash("T", "ITEM", "body")
    assert base != compute_content_hash("T2", "ITEM", "body")
    assert base != compute_content_hash("T", "SKILL", "body")
    assert base != compute_content_hash("T", "ITEM", "body!")


def test_helpers():
    assert slugify("Ünïcode & Spaces!") == "unicode-spaces"
    assert slugify("!!!") == "document"
    assert normalize_text("a\x00b") == "ab"


def test_load_documents(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps([VALID, {**VALID, "title": "Another"}]), encoding="utf-8")
    assert len(load_documents(good)) == 2
    single = tmp_path / "single.json"
    single.write_text(json.dumps(VALID), encoding="utf-8")
    assert len(load_documents(single)) == 1


@pytest.mark.parametrize(
    "text", ["not json", "[]", json.dumps({**VALID, "category": "NOPE"}), json.dumps([VALID, {}])]
)
def test_load_documents_rejects_bad_input(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DocumentLoadError):
        load_documents(path)


def test_load_documents_missing_file(tmp_path):
    with pytest.raises(DocumentLoadError):
        load_documents(tmp_path / "missing.json")
