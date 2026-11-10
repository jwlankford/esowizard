import re
from dataclasses import dataclass

from app.core.categories import ESOCategory

_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_MIN_BODY_BUDGET = 100


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    section: str | None
    token_count: int


def estimate_tokens(text: str) -> int:
    """Cheap approximation (~4 characters per token); only used for bookkeeping."""
    return max(1, (len(text) + 3) // 4)


def _split_sections(text: str) -> list[tuple[str | None, list[str]]]:
    """Split markdown-ish text into (heading path, blocks); blocks are blank-line separated."""
    sections: list[tuple[str | None, list[str]]] = []
    path: list[tuple[int, str]] = []
    current: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            current.append("\n".join(paragraph))
            paragraph.clear()

    def flush_section() -> None:
        flush_paragraph()
        if current:
            heading = " > ".join(title for _, title in path) or None
            sections.append((heading, list(current)))
            current.clear()

    for line in text.split("\n"):
        match = _HEADING.match(line)
        if match:
            flush_section()
            level = len(match.group(1))
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, match.group(2)))
        elif not line.strip():
            flush_paragraph()
        else:
            paragraph.append(line)
    flush_section()
    return sections


def _hard_split(text: str, budget: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for word in text.split(" "):
        while len(word) > budget:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:budget])
            word = word[budget:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) > budget:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _join_small(pieces: list[str], budget: int, separator: str) -> list[str]:
    joined: list[str] = []
    for piece in pieces:
        if joined and len(joined[-1]) + len(separator) + len(piece) <= budget:
            joined[-1] = f"{joined[-1]}{separator}{piece}"
        else:
            joined.append(piece)
    return joined


def _split_long(block: str, budget: int) -> list[str]:
    """Split a block exceeding ``budget`` at line, then sentence, then word boundaries."""
    if len(block) <= budget:
        return [block]
    lines: list[str] = []
    for line in block.split("\n"):
        if len(line) <= budget:
            lines.append(line)
            continue
        sentences: list[str] = []
        for sentence in _SENTENCE_END.split(line):
            sentences.extend(
                _hard_split(sentence, budget) if len(sentence) > budget else [sentence]
            )
        lines.extend(_join_small(sentences, budget, " "))
    return _join_small(lines, budget, "\n")


class Chunker:
    """Heading/paragraph-aware chunker with size limits and unit-level overlap."""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def context_header(title: str, category: ESOCategory | str, section: str | None) -> str:
        label = category.label if isinstance(category, ESOCategory) else str(category)
        header = f"Title: {title}\nCategory: {label}"
        return f"{header}\nSection: {section}" if section else header

    def chunk(self, title: str, category: ESOCategory | str, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section, blocks in _split_sections(text):
            header = self.context_header(title, category, section)
            budget = max(self.chunk_size - len(header) - 2, _MIN_BODY_BUDGET)
            units = [piece for block in blocks for piece in _split_long(block, budget)]
            for body in self._pack(units, budget):
                content = f"{header}\n\n{body}"
                chunks.append(Chunk(len(chunks), content, section, estimate_tokens(content)))
        return chunks

    def _pack(self, units: list[str], budget: int) -> list[str]:
        bodies: list[str] = []
        current: list[str] = []
        size = 0
        fresh = 0  # units in ``current`` that are not carried-over overlap
        for unit in units:
            added = len(unit) + (2 if current else 0)
            if current and size + added > budget:
                if fresh:
                    bodies.append("\n\n".join(current))
                current = self._overlap(current, len(unit), budget) if fresh else []
                size = len("\n\n".join(current))
                fresh = 0
                added = len(unit) + (2 if current else 0)
            current.append(unit)
            size += added
            fresh += 1
        if fresh:
            bodies.append("\n\n".join(current))
        return bodies

    def _overlap(self, units: list[str], next_len: int, budget: int) -> list[str]:
        carried: list[str] = []
        total = 0
        for unit in reversed(units):
            total += len(unit) + (2 if carried else 0)
            if total > self.chunk_overlap or total + 2 + next_len > budget:
                break
            carried.insert(0, unit)
        return carried
