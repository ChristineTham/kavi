"""Markdown structure: cut a document into translatable blocks and put it back together.

The unit of translation is the paragraph (a run of plain lines with the same blockquote prefix), a heading,
a list item or a table cell. Code fences, HTML/JSX blocks, horizontal rules, blank lines and anything that
is only markup pass through untouched. Inline constructs that must survive verbatim — code spans, links,
footnote markers, tags, URLs — are swapped for ``%%n%%`` placeholders before the text reaches a model and
restored afterwards; a translation that loses or invents a placeholder is rejected by the caller.

Sentence splitting is for long paragraphs and for the word-by-word review: Pāḷi editions end sentences
with ``.``, ``?`` and ``!`` and mark verse pādas with ``|``/``||`` or a hard line break.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------------------
# Inline protection
# --------------------------------------------------------------------------------------

PH_RE = re.compile(r"%%\s*(\d+)\s*%%")
PROTECT_PATTERNS = [
    re.compile(r":badge\[[^\]\n]*\]\{[^}\n]*\}"),      # starlight-heading-badges
    re.compile(r"`[^`\n]+`"),                           # inline code
    re.compile(r"<[^<>\n]+>"),                          # HTML / JSX tags
    re.compile(r"!?\[[^\]\n]*\]\([^)\n]*\)"),           # links / images
    re.compile(r"\[\^[^\]\n]+\]"),                      # footnote references
    re.compile(r"https?://\S+"),                        # bare URLs
    re.compile(r"\{[^{}\n]*\}"),                        # MDX expressions
]


def protect(text: str) -> tuple[str, list[str]]:
    kept: list[str] = []

    def sub(m: re.Match) -> str:
        kept.append(m.group(0))
        return f"%%{len(kept) - 1}%%"

    for pat in PROTECT_PATTERNS:
        text = pat.sub(sub, text)
    return text, kept


def restore(text: str, kept: list[str]) -> str:
    for _ in range(len(kept) + 1):
        if not PH_RE.search(text):
            break
        text = PH_RE.sub(lambda m: kept[int(m.group(1))] if int(m.group(1)) < len(kept) else m.group(0), text)
    return text


def placeholders_ok(output: str, masked: str) -> bool:
    return sorted(int(m.group(1)) for m in PH_RE.finditer(output)) == sorted(int(m.group(1)) for m in PH_RE.finditer(masked))


# --------------------------------------------------------------------------------------
# Block structure
# --------------------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HR_RE = re.compile(r"^\s{0,3}([-*_])\s*(?:\1\s*){2,}$")
HEADING_RE = re.compile(r"^(\s{0,3}#{1,6}\s+)(.*?)\s*$")
QUOTE_RE = re.compile(r"^((?:\s*>\s?)+)(.*)$")
LIST_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)(.*)$")
MDX_RE = re.compile(r"^\s*(?:import|export)\s")
TABLE_RE = re.compile(r"^\s*\|")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
ANCHOR_ONLY_RE = re.compile(r"^\s*<[^>]*>\s*$")
HARDBREAK_RE = re.compile(r"(\s*\\|\s{2,})$")
HAS_LETTERS_RE = re.compile(r"[^\W\d_]", re.UNICODE)
PALI_LETTER_RE = re.compile(r"[āīūṃṅñṭḍṇḷ]")


@dataclass
class Block:
    kind: str                      # 'verbatim' | 'heading' | 'list' | 'para' | 'table'
    lines: list[str]               # the original lines
    prefix: str = ""               # blockquote / heading / list marker to put back
    text: str = ""                 # translatable text (paragraph lines joined with \n, hard breaks stripped)
    breaks: list[str] = field(default_factory=list)   # the hard-break token of each paragraph line
    cells: list[list[str]] = field(default_factory=list)  # table: rows of cells
    translation: str | None = None
    cell_translations: list[list[str | None]] = field(default_factory=list)

    @property
    def translatable(self) -> bool:
        return self.kind in ("heading", "list", "para", "table") and bool(HAS_LETTERS_RE.search(self.text or " ".join(c for r in self.cells for c in r)))


def split_quote(line: str) -> tuple[str, str]:
    m = QUOTE_RE.match(line)
    return (m.group(1), m.group(2)) if m else ("", line)


def is_structural(rest: str) -> bool:
    s = rest.strip()
    if not s:
        return True
    return bool(HR_RE.match(rest) or MDX_RE.match(rest) or ANCHOR_ONLY_RE.match(rest))


def jsx_block_len(lines: list[str], start: int) -> int:
    _, rest = split_quote(lines[start])
    if not rest.lstrip().startswith("<"):
        return 0
    depth = 0
    for offset in range(start, len(lines)):
        _, body = split_quote(lines[offset])
        depth += body.count("<") - body.count(">")
        if depth <= 0:
            return offset - start + 1
    return 1


def parse_markdown(text: str) -> list[Block]:
    lines = text.split("\n")
    blocks: list[Block] = []
    i = 0

    # frontmatter passes through verbatim
    if lines and lines[0].strip() == "---":
        close = next((j for j in range(1, len(lines)) if lines[j].strip() == "---"), None)
        if close is not None:
            blocks.append(Block("verbatim", lines[: close + 1]))
            i = close + 1

    while i < len(lines):
        line = lines[i]
        quote, rest = split_quote(line)

        fence = FENCE_RE.match(rest)
        if fence:
            marker = fence.group(2)
            j = i + 1
            while j < len(lines):
                _, body = split_quote(lines[j])
                j += 1
                if body.strip().startswith(marker):
                    break
            blocks.append(Block("verbatim", lines[i:j]))
            i = j
            continue

        span = jsx_block_len(lines, i)
        if span:
            blocks.append(Block("verbatim", lines[i: i + span]))
            i += span
            continue

        if is_structural(rest):
            blocks.append(Block("verbatim", [line]))
            i += 1
            continue

        if TABLE_RE.match(rest):
            j = i
            rows: list[list[str]] = []
            while j < len(lines):
                q2, r2 = split_quote(lines[j])
                if q2 != quote or not TABLE_RE.match(r2):
                    break
                j += 1
            block_lines = lines[i:j]
            for l in block_lines:
                _, r2 = split_quote(l)
                if TABLE_SEP_RE.match(r2):
                    rows.append([])
                else:
                    rows.append([c.strip() for c in r2.strip().strip("|").split("|")])
            blocks.append(Block("table", block_lines, prefix=quote, cells=rows))
            i = j
            continue

        heading = HEADING_RE.match(rest)
        if heading:
            blocks.append(Block("heading", [line], prefix=quote + heading.group(1), text=heading.group(2)))
            i += 1
            continue

        item = LIST_RE.match(rest)
        if item:
            blocks.append(Block("list", [line], prefix=quote + item.group(1), text=item.group(2).strip()))
            i += 1
            continue

        group: list[str] = []
        j = i
        while j < len(lines):
            q2, r2 = split_quote(lines[j])
            if q2 != quote or is_structural(r2) or HEADING_RE.match(r2) or LIST_RE.match(r2) or TABLE_RE.match(r2):
                break
            if FENCE_RE.match(r2) or jsx_block_len(lines, j):
                break
            group.append(r2)
            j += 1
        breaks = [(m.group(0) if (m := HARDBREAK_RE.search(g)) else "") for g in group]
        stripped = [HARDBREAK_RE.sub("", g) for g in group]
        blocks.append(Block("para", lines[i:j], prefix=quote, text="\n".join(stripped), breaks=breaks))
        i = j
    return blocks


def render(blocks: list[Block]) -> str:
    out: list[str] = []
    for b in blocks:
        if b.kind == "verbatim" or (b.translation is None and not b.cell_translations):
            out.extend(b.lines)
        elif b.kind in ("heading", "list"):
            out.append(b.prefix + (b.translation or b.text))
        elif b.kind == "para":
            parts = (b.translation or b.text).split("\n")
            if len(parts) == len(b.breaks):
                suffixes = b.breaks
            else:
                canonical = next((x for x in b.breaks[:-1] if x), "")
                suffixes = [canonical] * (len(parts) - 1) + [b.breaks[-1] if b.breaks else ""]
            out.extend(b.prefix + p + s for p, s in zip(parts, suffixes))
        elif b.kind == "table":
            for row, line, trs in zip(b.cells, b.lines, b.cell_translations or [[None] * len(r) for r in b.cells]):
                if not row:
                    out.append(line)
                    continue
                cells = [t if t is not None else c for c, t in zip(row, trs)]
                out.append(b.prefix + "| " + " | ".join(cells) + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------------------
# Sentences
# --------------------------------------------------------------------------------------

SENT_END_RE = re.compile(r"[.?!।॥][”’\"')\]]*(?:\s+(?=\S)|$)|\s*\|\|?\s+(?=\S)|\n")
ABBREV_RE = re.compile(r"\b(?:[A-Z][a-z]?|Ma|Saṃ|Aṅ|Dī|Vi|Su|Ni|Pe|Ud|Iti|Dha|Vibh|Pu|Dhs|Ma\.\s*Ni)\.$")


def split_sentences(text: str) -> list[str]:
    """Sentences (or verse lines) of a paragraph, punctuation kept, order kept."""
    pieces: list[str] = []
    start = 0
    for m in SENT_END_RE.finditer(text):
        cand = text[start:m.end()].strip()
        if not cand:
            start = m.end()
            continue
        if m.group(0) != "\n" and ABBREV_RE.search(text[start:m.start() + 1].strip()):
            continue                      # "Ma. Ni." style abbreviation, not a sentence end
        pieces.append(cand)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        pieces.append(tail)
    return pieces or [text.strip()]


def word_count(text: str) -> int:
    return len(re.findall(r"[^\W\d_]+", PH_RE.sub(" ", text)))
