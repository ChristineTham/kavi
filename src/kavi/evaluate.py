"""Score a translation against a reference translation, so the harness can be improved by measurement.

* **chrF** (Popović 2015): character n-gram F-score (n = 1…6, β = 2), the standard reference-based metric that is
  robust to word-order and morphology differences — computed on the plain text with Markdown stripped;
* **word F1**: overlap of lower-cased word tokens;
* **conventions**: how many of the checker's findings the candidate still shows against its Pāḷi source (names,
  honorifics, `term` (gloss) forms, particles, tense) — zero is the target;
* **glossary agreement**: for each glossary term in the source, whether the candidate and the reference render it
  alike.

Paragraphs are aligned by their leading number ("3.", "95.") when both sides have one, otherwise by order.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .dpd import DPD, analyse_text
from .lint import lint
from .segment import parse_markdown

MD_STRIP = [(re.compile(r"`([^`]*)`"), r"\1"), (re.compile(r"[*_]{1,3}([^*_]+)[*_]{1,3}"), r"\1"),
            (re.compile(r"!?\[([^\]]*)\]\([^)]*\)"), r"\1"), (re.compile(r"^\s{0,3}#{1,6}\s*", re.M), ""),
            (re.compile(r"^\s*>\s?", re.M), ""), (re.compile(r"\\\n"), "\n"), (re.compile(r"%%\d+%%"), " ")]


def plain(text: str) -> str:
    for pat, rep in MD_STRIP:
        text = pat.sub(rep, text)
    return re.sub(r"\s+", " ", text).strip()


def _ngrams(s: str, n: int) -> Counter:
    s = s.replace(" ", "")
    return Counter(s[i: i + n] for i in range(len(s) - n + 1))


def chrf(candidate: str, reference: str, max_n: int = 6, beta: float = 2.0) -> float:
    """chrF score in 0–100 over the whole text."""
    c, r = plain(candidate).lower(), plain(reference).lower()
    if not c or not r:
        return 0.0
    precs, recs = [], []
    for n in range(1, max_n + 1):
        cn, rn = _ngrams(c, n), _ngrams(r, n)
        if not cn or not rn:
            continue
        overlap = sum((cn & rn).values())
        precs.append(overlap / max(sum(cn.values()), 1))
        recs.append(overlap / max(sum(rn.values()), 1))
    if not precs:
        return 0.0
    p, rc = sum(precs) / len(precs), sum(recs) / len(recs)
    if p + rc == 0:
        return 0.0
    return 100 * (1 + beta ** 2) * p * rc / (beta ** 2 * p + rc)


def word_f1(candidate: str, reference: str) -> float:
    cw = Counter(re.findall(r"[^\W\d_]+", plain(candidate).lower()))
    rw = Counter(re.findall(r"[^\W\d_]+", plain(reference).lower()))
    overlap = sum((cw & rw).values())
    if not cw or not rw or not overlap:
        return 0.0
    p, r = overlap / sum(cw.values()), overlap / sum(rw.values())
    return 100 * 2 * p * r / (p + r)


NUM_RE = re.compile(r"^\s*(\d+)\.\s")


def paragraphs(text: str) -> list[tuple[str | None, str]]:
    """(leading number or None, text) for each paragraph-like block. In a numbered text, an unnumbered block
    continues the numbered block before it (a reference that sets a list out as separate lines)."""
    out: list[tuple[str | None, str]] = []
    numbered = False
    for b in parse_markdown(text):
        if b.kind in ("para", "list", "heading") and b.text.strip():
            m = NUM_RE.match(b.prefix + b.text) or NUM_RE.match(b.text)
            if m:
                numbered = True
                out.append((m.group(1), b.text))
            elif numbered and out and b.kind != "heading":
                out[-1] = (out[-1][0], out[-1][1] + "\n" + b.text)
            else:
                out.append((None, b.text))
    return out


def align(cand: list[tuple[str | None, str]], ref: list[tuple[str | None, str]]) -> list[tuple[str, str, str]]:
    """(label, candidate, reference) pairs: by number when both sides are numbered, otherwise by order."""
    if any(n for n, _ in cand) and any(n for n, _ in ref):
        rnum = {n: t for n, t in ref if n}
        pairs = [(n, t, rnum[n]) for n, t in cand if n and n in rnum]
        if pairs:
            return pairs
    return [(str(i + 1), c[1], r[1]) for i, (c, r) in enumerate(zip(cand, ref))]


@dataclass
class Score:
    chrf: float
    word_f1: float
    convention_findings: int
    convention_detail: list[str] = field(default_factory=list)
    glossary_agreement: tuple[int, int] = (0, 0)     # (agreeing, checked)
    per_paragraph: list[tuple[str, float]] = field(default_factory=list)

    def table(self) -> str:
        lines = ["| metric | value |", "| --- | --- |",
                 f"| chrF (0–100) | {self.chrf:.1f} |", f"| word F1 (0–100) | {self.word_f1:.1f} |",
                 f"| convention findings left | {self.convention_findings} |",
                 f"| glossary terms rendered as in the reference | {self.glossary_agreement[0]}/{self.glossary_agreement[1]} |"]
        if self.per_paragraph:
            lines += ["", "| paragraph | chrF |", "| --- | --- |"] + [f"| {k} | {v:.1f} |" for k, v in self.per_paragraph]
        if self.convention_detail:
            lines += ["", "Convention findings:"] + [f"- {d}" for d in self.convention_detail[:20]]
        return "\n".join(lines)


def evaluate(candidate: str, reference: str, source: str | None = None, dpd: DPD | None = None,
             glossary: dict[str, str] | None = None, alternatives: dict[str, list[str]] | None = None) -> Score:
    cand_p, ref_p = paragraphs(candidate), paragraphs(reference)
    pairs = align(cand_p, ref_p)
    per = [(label, chrf(c, r)) for label, c, r in pairs]
    score = Score(chrf(candidate, reference), word_f1(candidate, reference), 0, per_paragraph=per)
    if source and dpd is not None:
        src_p = paragraphs(source)
        findings: list[str] = []
        agree = checked = 0
        cand_by_label = {label: c for label, c, _ in pairs}
        ref_by_label = {label: r for label, _, r in pairs}
        for label, s, _ in align(src_p, cand_p):
            an = analyse_text(dpd, s)
            c = cand_by_label.get(label, "")
            _, fs = lint(an, c, glossary, apply=False, alternatives=alternatives)
            findings += [f"[{label}] {f}" for f in fs]
            r = ref_by_label.get(label, "")
            for a in an:
                h = a.governing(glossary)
                if h is not None and glossary and h.stem in glossary:
                    g = glossary[h.stem].lower()
                    in_ref = g in r.lower() or f"`{a.surface.strip(chr(8217))}`".lower() in r.lower()
                    in_cand = g in c.lower() or f"`{a.surface.strip(chr(8217))}`".lower() in c.lower()
                    if in_ref:
                        checked += 1
                        agree += int(in_cand)
        score.convention_findings = len(findings)
        score.convention_detail = findings
        score.glossary_agreement = (agree, checked)
    return score
