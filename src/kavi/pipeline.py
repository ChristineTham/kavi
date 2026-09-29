"""The translation pipeline.

For each translatable block of the document:

1. the inline markup is protected with placeholders and the block's words are analysed with the DPD
   (sandhi resolved with the deconstructor and Kaccāyana's rules);
2. the translate model produces a literal draft, with the word analysis as in-context reference; a long
   paragraph is translated sentence by sentence;
3. consecutive drafts are gathered into batches and the instruction-tuned model reviews each batch against the
   Pāli and the analysis, returning issues and a revised text;
4. step 3 repeats until the reviewer reports no issues or the round limit is reached.

Placeholders, Markdown structure and hard line breaks are checked on the way back; a model output that loses
them is discarded and the previous text kept.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import Settings
from .dpd import DPD, Analysis, analyse_text, analysis_table
from .lint import Finding, lint
from .models import (ModelPool, is_degenerate, is_meta, is_mitra_translate, parse_review, review_prompt,
                     strip_wrapper, translate_messages_generic, translate_prompt)
from .segment import (Block, PH_RE, parse_markdown, placeholders_ok, protect, render, restore, split_sentences,
                      word_count)

Progress = Callable[[str], None]


@dataclass
class Round:
    issues: list[str]              # what the reviewer reported (for this segment)
    before: str
    after: str
    seconds: float = 0.0
    lint_before: list[str] = field(default_factory=list)   # checker findings handed to the reviewer
    lint_after: list[str] = field(default_factory=list)    # checker findings still open after the revision


@dataclass
class Unit:
    """One translatable piece: a paragraph, heading, list item or table cell."""
    block: Block
    cell: tuple[int, int] | None          # (row, col) for a table cell
    source: str                            # text as it stands in the document (with inline markup)
    masked: str                            # with placeholders
    kept: list[str]
    analyses: list[Analysis] = field(default_factory=list)
    draft: str = ""                        # the translate model's output (masked)
    current: str = ""                      # the latest accepted translation (masked)
    rounds: list[Round] = field(default_factory=list)
    from_cache: bool = False
    rejected: list[str] = field(default_factory=list)
    lint: list[Finding] = field(default_factory=list)      # findings on the draft (fixes applied, asks open)
    open_findings: list[Finding] = field(default_factory=list)
    kept_source: bool = False                              # a title made only of names/terms: not translated

    @property
    def final(self) -> str:
        return restore(self.current or self.draft or self.masked, self.kept)

    @property
    def words(self) -> int:
        return word_count(self.masked)


@dataclass
class Result:
    markdown: str
    units: list[Unit]
    seconds: float
    model_calls: int

    @property
    def analyses(self) -> list[Analysis]:
        seen: set[str] = set()
        out = []
        for u in self.units:
            for a in u.analyses:
                if a.key not in seen:
                    seen.add(a.key)
                    out.append(a)
        return out

    def table(self) -> str:
        return analysis_table(self.analyses)

    def report(self) -> str:
        lines = []
        for i, u in enumerate(self.units, 1):
            lines.append(f"### Segment {i}\n\n> {u.source}\n\n{u.final}")
            if u.from_cache:
                lines.append("_(from cache)_")
            if u.draft and u.draft != u.current:
                lines.append(f"\nDraft: {restore(u.draft, u.kept)}")
            if u.lint:
                lines.append("\n**Checker on the draft:**")
                lines.extend(f"- {'fixed' if f.severity == 'fix' else 'to fix'}: {f}" for f in u.lint)
            for r_i, r in enumerate(u.rounds, 1):
                head = f"\n**Review round {r_i}** ({r.seconds:.0f}s): "
                lines.append(head + ("no issues reported" if not r.issues else ""))
                lines.extend(f"- {iss}" for iss in r.issues)
                if r.after != r.before:
                    lines.append(f"\nRevised to: {restore(r.after, u.kept)}")
                if r.lint_after:
                    lines.append("Still open after this round: " + "; ".join(r.lint_after))
            if u.open_findings:
                lines.append("\n**Unresolved:** " + "; ".join(str(f) for f in u.open_findings))
            for rej in u.rejected:
                lines.append(f"- rejected model output: {rej}")
            lines.append("")
        return "\n".join(lines)


class Translator:
    def __init__(self, settings: Settings, dpd: DPD, models: ModelPool, progress: Progress | None = None,
                 use_cache: bool = True):
        self.s = settings
        self.dpd = dpd
        self.models = models
        self.progress = progress or (lambda msg: sys.stderr.write(msg + "\n"))
        self.calls = 0
        self.cache_path = settings.cache_dir / "translations.json" if use_cache else None
        self.cache: dict[str, dict] = {}
        if self.cache_path and self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.cache = {}

    # -- cache ------------------------------------------------------------------------

    def _key(self, masked: str) -> str:
        raw = "\x00".join([masked, Path(self.s.translate_model).name, Path(self.s.eval_model).name,
                           str(self.s.max_rounds), str(self.s.thinking), "|".join(self.s.glossary_terms)])
        return hashlib.sha256(raw.encode()).hexdigest()

    def save_cache(self) -> None:
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    # -- analysis ---------------------------------------------------------------------

    def analyse(self, text: str) -> list[Analysis]:
        return analyse_text(self.dpd, text)

    # -- units --------------------------------------------------------------------------

    def _units(self, blocks: list[Block]) -> list[Unit]:
        units: list[Unit] = []
        for b in blocks:
            if b.kind == "table":
                b.cell_translations = [[None] * len(r) for r in b.cells]
                for ri, row in enumerate(b.cells):
                    for ci, cell in enumerate(row):
                        if re.search(r"[^\W\d_]", cell) and len(cell.split()) >= 1 and not re.fullmatch(r"[\W\d_%]+", cell):
                            masked, kept = protect(cell)
                            if re.search(r"[^\W\d_]", PH_RE.sub("", masked)):
                                units.append(Unit(b, (ri, ci), cell, masked, kept))
            elif b.translatable:
                masked, kept = protect(b.text)
                if re.search(r"[^\W\d_]", PH_RE.sub("", masked)):
                    units.append(Unit(b, None, b.text, masked, kept))
        return units

    # -- translation ----------------------------------------------------------------------

    def _translate_one(self, masked: str, analyses: list[Analysis], single_line: bool, markdown: bool,
                       context: list[tuple[str, str]] | None = None) -> str | None:
        model = self.models.get("translate")
        has_ph = bool(PH_RE.search(masked))
        if is_mitra_translate(model.path):
            messages = [{"role": "user", "content": translate_prompt(
                masked, analyses, has_ph, markdown, extra_terms=self.s.glossary_terms, glossary=self.s.glossary_map,
                context=context)}]
        else:
            messages = translate_messages_generic(masked, analyses, has_ph, markdown, extra_terms=self.s.glossary_terms,
                                                  glossary=self.s.glossary_map, context=context)
        for temp in (self.s.temperature, 0.2):
            self.calls += 1
            reply = model.chat(messages, max_tokens=self.s.max_tokens, temperature=temp, thinking=self.s.thinking)
            if reply.finish_reason == "length":
                continue
            out = strip_wrapper(reply.text)
            if not out or is_degenerate(out, masked) or is_meta(out):
                continue
            if single_line and "\n" in out:
                out = " ".join(out.split())
            if placeholders_ok(out, masked):
                return out
        return None

    def _title_of_names(self, unit: Unit) -> bool:
        """A heading or cell of up to three words that are all names, honorifics, technical terms or numbers."""
        if unit.block.kind not in ("heading", "table") or unit.words > 3:
            return False
        words = [a for a in unit.analyses]
        if not words:
            return False
        for a in words:
            h = a.governing(self.s.glossary_map)
            if h is None or not (h.kind or h.stem in self.s.glossary_map):
                return False
        return True

    def draft(self, unit: Unit, context: list[tuple[str, str]] | None = None) -> None:
        """``context``: the preceding segments (Pāḷi, current translation), newest last, for consistency."""
        if self._title_of_names(unit):
            unit.draft = unit.masked
            unit.kept_source = True
            fixed, findings = lint(unit.analyses, unit.draft, self.s.glossary_map, alternatives=self.s.glossary_alternatives)
            unit.current = fixed if placeholders_ok(fixed, unit.masked) else unit.draft
            unit.lint = findings
            unit.open_findings = []
            return
        single = unit.block.kind in ("heading", "list", "table")
        markdown = "*" in unit.masked or "_" in unit.masked
        if unit.words > self.s.sentence_words and "\n" not in unit.masked:
            parts = split_sentences(unit.masked)
        else:
            parts = [unit.masked]
        outs = []
        ctx = list(context or [])
        for part in parts:
            an = [a for a in unit.analyses if a.key in {k.lower() for k in _keys(part)}] if len(parts) > 1 else unit.analyses
            out = self._translate_one(part, an or unit.analyses, single, markdown, ctx[-self.s.context_segments:] or None)
            if out is not None and len(parts) > 1:
                ctx.append((part, out))                     # earlier sentences of a long paragraph guide the later ones
            if out is None:
                unit.rejected.append(f"translate model gave no usable output for: {part[:60]}")
                out = part                       # leave the source in place
            outs.append(out)
        unit.draft = " ".join(outs) if len(parts) > 1 else outs[0]
        fixed, findings = lint(unit.analyses, unit.draft, self.s.glossary_map, alternatives=self.s.glossary_alternatives)
        if placeholders_ok(fixed, unit.masked):
            unit.current = fixed
        else:
            unit.current = unit.draft
        unit.lint = findings
        unit.open_findings = [f for f in findings if f.severity == "ask"]

    # -- review -------------------------------------------------------------------------------

    def review_batch(self, units: list[Unit]) -> bool:
        """One review round over a batch. Returns True if the reviewer found issues (and revisions were applied)."""
        model = self.models.get("review")
        seen: set[str] = set()
        analyses = []
        for u in units:
            for a in u.analyses:
                if a.key not in seen:
                    seen.add(a.key)
                    analyses.append(a)
        units = [u for u in units if not u.kept_source]
        if not units:
            return False
        segments = [(u.masked, u.current) for u in units]
        known = {n: [str(f) for f in u.open_findings] for n, u in enumerate(units, 1) if u.open_findings}
        prompt = review_prompt(segments, analyses, extra_terms=self.s.glossary_terms, glossary=self.s.glossary_map, known=known)
        t0 = time.time()
        self.calls += 1
        reply = model.chat([{"role": "system", "content": "You are a meticulous reviewer of Pāli-to-English translations."},
                            {"role": "user", "content": prompt}],
                           max_tokens=self.s.max_tokens * 2, temperature=self.s.temperature, thinking=self.s.thinking)
        res = parse_review(reply.text, len(units))
        seconds = time.time() - t0
        if not res.parsed:
            for u in units:
                u.rejected.append("review output could not be parsed" + (" (truncated)" if reply.finish_reason == "length" else ""))
            return False
        changed = False
        still_open = False
        for n, u in enumerate(units, 1):
            before = u.current
            after = res.revised.get(n, before).strip()
            mine = [i for i in res.issues if re.search(rf"\[{n}\]|segment {n}\b", i, re.I)] or ([] if len(units) > 1 else res.issues)
            if after and after != before:
                if placeholders_ok(after, u.masked) and not is_degenerate(after, u.masked) and not is_meta(after):
                    if u.block.kind in ("heading", "list", "table") and "\n" in after:
                        after = " ".join(after.split())
                    changed = True
                else:
                    u.rejected.append(f"revision rejected (placeholders/degenerate): {after[:60]}")
                    after = before
            # the checker runs again on the revision: its string fixes are applied, its open asks carry over
            fixed, findings = lint(u.analyses, after, self.s.glossary_map, alternatives=self.s.glossary_alternatives)
            if fixed != after and placeholders_ok(fixed, u.masked):
                after = fixed
                changed = True
            u.current = after
            u.open_findings = [f for f in findings if f.severity == "ask"]
            if u.open_findings:
                still_open = True
            u.rounds.append(Round(mine, before, after, seconds, lint_before=known.get(n, []),
                                  lint_after=[str(f) for f in u.open_findings]))
        revised = sum(1 for n, u in enumerate(units, 1) if res.revised.get(n, "").strip() not in ("", u.rounds[-1].before))
        self.progress(f"  reviewer: {len(res.issues)} issue(s), {revised} segment(s) revised; checker: "
                      f"{sum(len(u.open_findings) for u in units)} finding(s) still open")
        # another round is worth running only if this one changed something and problems remain
        return changed and (bool(res.issues) or still_open)

    def _batches(self, units: list[Unit]) -> list[list[Unit]]:
        batches: list[list[Unit]] = []
        cur: list[Unit] = []
        words = 0
        for u in units:
            if cur and words + u.words > self.s.eval_batch_words:
                batches.append(cur)
                cur, words = [], 0
            cur.append(u)
            words += u.words
        if cur:
            batches.append(cur)
        return batches

    # -- document -------------------------------------------------------------------------------

    def translate_markdown(self, text: str, review: bool = True) -> Result:
        t0 = time.time()
        blocks = parse_markdown(text)
        units = self._units(blocks)
        todo: list[Unit] = []
        for i, u in enumerate(units, 1):
            key = self._key(u.masked)
            if key in self.cache:
                c = self.cache[key]
                u.current = u.draft = c["translation"]
                u.from_cache = True
                u.analyses = self.analyse(u.source)
                continue
            todo.append(u)
        self.progress(f"{len(units)} segments, {len(todo)} to translate ({len(units) - len(todo)} cached)")
        recent: list[tuple[str, str]] = []                  # (Pāḷi, translation) of the preceding prose segments
        for i, u in enumerate(todo, 1):
            u.analyses = self.analyse(u.source)
            unknown = sum(1 for a in u.analyses if not a.found)
            self.progress(f"[{i}/{len(todo)}] {u.words} words, {len(u.analyses)} distinct, {unknown} unknown: translating …")
            self.draft(u, recent[-self.s.context_segments:] or None)
            if u.block.kind in ("para", "list") and not u.kept_source and u.words >= 4:
                recent.append((u.masked, u.current))
            fixes = sum(1 for f in u.lint if f.severity == "fix")
            if u.lint:
                self.progress(f"  checker: {fixes} fix(es) applied, {len(u.open_findings)} for the reviewer")
        if review and self.s.max_rounds > 0 and todo:
            if self.s.translate_model != self.s.eval_model and self.s.release_translator:
                self.models.release("translate")
            for bi, batch in enumerate(self._batches(todo), 1):
                for r in range(1, self.s.max_rounds + 1):
                    self.progress(f"review batch {bi}, round {r} ({len(batch)} segments) …")
                    found = self.review_batch(batch)
                    if not found:
                        break
        for u in todo:
            self.cache[self._key(u.masked)] = {"translation": u.current, "source": u.masked}
        self.save_cache()
        for u in units:
            if u.cell is not None:
                ri, ci = u.cell
                u.block.cell_translations[ri][ci] = u.final
            else:
                u.block.translation = u.final
        return Result(render(blocks), units, time.time() - t0, self.calls)


def _keys(text: str) -> list[str]:
    from .dpd import tokens, normalise
    return [normalise(w) for w in tokens(text)]
