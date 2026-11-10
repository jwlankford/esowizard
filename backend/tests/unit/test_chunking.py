import itertools

import pytest

from app.core.categories import ESOCategory
from app.services.knowledge.chunking import Chunker


def test_headings_start_new_chunks_and_context_is_preserved():
    text = (
        "# Intro\n\nFirst paragraph.\n\n## Details\n\n- item one\n- item two\n\nSecond paragraph."
    )
    chunks = Chunker(500, 50).chunk("Synthetic Title", ESOCategory.GEAR_SET, text)
    assert [chunk.section for chunk in chunks] == ["Intro", "Intro > Details"]
    for chunk in chunks:
        assert "Title: Synthetic Title" in chunk.content
        assert "Category: Gear Set" in chunk.content
        assert f"Section: {chunk.section}" in chunk.content
    assert "- item one\n- item two" in chunks[1].content
    assert [chunk.index for chunk in chunks] == [0, 1]
    assert all(chunk.token_count > 0 for chunk in chunks)


def test_no_heading_document_is_chunked():
    chunks = Chunker(500, 50).chunk("T", ESOCategory.ITEM, "Alpha.\n\nBeta.")
    assert len(chunks) == 1
    assert chunks[0].section is None
    assert "Section:" not in chunks[0].content


def test_size_limit_and_paragraph_boundaries():
    paragraphs = [f"Paragraph {n} " + "word " * 30 for n in range(10)]
    chunks = Chunker(400, 0).chunk(
        "T", ESOCategory.ITEM, "\n\n".join(p.strip() for p in paragraphs)
    )
    assert len(chunks) > 1
    assert all(len(chunk.content) <= 400 for chunk in chunks)
    joined = "\n".join(chunk.content for chunk in chunks)
    assert all(paragraph.strip() in joined for paragraph in paragraphs)


def test_overlap_repeats_trailing_unit():
    paragraphs = [f"P{n} " + "x" * 80 for n in range(6)]
    chunks = Chunker(300, 120).chunk("T", ESOCategory.ITEM, "\n\n".join(paragraphs))
    assert len(chunks) > 1
    for previous, current in itertools.pairwise(chunks):
        assert previous.content.split("\n\n")[-1] in current.content


def test_oversized_paragraph_is_split_without_losing_sentences():
    text = "".join(f"This is sentence number {n}. " for n in range(60)).strip()
    chunks = Chunker(300, 40).chunk("T", ESOCategory.ITEM, text)
    assert len(chunks) > 1
    assert all(len(chunk.content) <= 300 for chunk in chunks)
    body = " ".join(chunk.content.split("\n\n", 1)[1] for chunk in chunks)
    for n in range(60):
        assert f"sentence number {n}." in body


def test_unbroken_token_is_hard_split():
    chunks = Chunker(300, 0).chunk("T", ESOCategory.ITEM, "a" * 1000)
    assert len(chunks) > 1
    assert all(len(chunk.content) <= 300 for chunk in chunks)


def test_invalid_configuration():
    with pytest.raises(ValueError):
        Chunker(100, 100)
    with pytest.raises(ValueError):
        Chunker(0, 0)


def test_long_title_and_section_never_exceed_chunk_size():
    text = "# " + "S" * 400 + "\n\n" + "word " * 200
    chunks = Chunker(300, 30).chunk("T" * 500, ESOCategory.FISHING, text)
    assert chunks
    assert all(len(c.content) <= 300 for c in chunks)
