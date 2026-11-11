"""The unified translation pipeline.

Regardless of whether the user chooses interlinear or prose output:
1. Every translatable block is segmented into units (sentences, verse lines, headings, list items, or table cells).
2. The units are analysed word by word using the language lexicon (DPD for Pāḷi; vidyut and Cologne for Sanskrit).
3. The unified model selects candidate parses, generates word-by-word glosses, and drafts the translation.
4. An agentic self-improving loop (review harness + revision turns) evaluates and improves the translation
   against the candidate parses, glossary rulings, and conventions.
5. Deterministic linting enforces technical terms and house styles.

Output rendering:
- Prose-only output (default): the interlinear lines are omitted, producing clean translated prose
  with the Markdown formatting and layout preserved exactly from the original text.
- Interlinear output (--interlinear): four lines per unit (source, analysis symbols, glosses, translated prose).
- Both forms are always accessible via Result.markdown, Result.en_markdown, and Result.interlinear_markdown.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from .config import Settings
from .dpd import DPD, Analysis, analyse_text, analysis_table
from .glossary import honorific_form
from .interlinear import (
    Token, Parse, analyse_tokens, format_mantra, load_segments, match_segments,
    modern, parse_answer, prompt_for, reconcile_case, system_prompt, units_pieces,
    _clean_quotes, _conventional,
)
from .language import LANGUAGE, set_language
from .lint import Finding, lint, HONORIFICS, HONORIFIC_MEANINGS, _clean_dict_gloss
from .models import (
    ModelPool, clear_metal_cache, is_degenerate, is_meta, is_mitra_translate,
    parse_review, review_prompt, strip_wrapper, translate_messages_generic,
    translate_messages_revision, translate_prompt,
)
from .segment import (
    Block, HAS_LETTERS_RE, PH_RE, parse_markdown, placeholders_ok, protect,
    render, restore, split_sentences, word_count,
)

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
    """One translatable piece: a sentence, heading, list item or table cell."""
    block: Block
    cell: tuple[int, int] | None = None          # (row, col) for a table cell
    source: str = ""                            # text as it stands in the document
    masked: str = ""                            # with placeholders
    kept: list[str] = field(default_factory=list)
    number: str = ""                            # e.g. "1.1" or "0.2"
    verse: bool = False
    tokens: list[Token] = field(default_factory=list)
    analyses_override: list[Analysis] | None = None
    draft: str = ""
    current: str = ""
    initial_draft: str = ""
    rounds: list[Round] = field(default_factory=list)
    from_cache: bool = False
    rejected: list[str] = field(default_factory=list)
    lint: list[Finding] = field(default_factory=list)
    open_findings: list[Finding] = field(default_factory=list)
    kept_source: bool = False
    raw: str = ""

    @property
    def text(self) -> str:
        return self.source

    @property
    def translation(self) -> str:
        return self.current or self.draft or self.source

    @translation.setter
    def translation(self, val: str) -> None:
        self.current = val

    @property
    def final(self) -> str:
        text = self.current or self.draft or self.masked or self.source
        return restore(text, self.kept) if self.kept else text

    @property
    def words(self) -> int:
        return word_count(self.masked or self.source)

    @property
    def analyses(self) -> list[Analysis]:
        if self.analyses_override is not None:
            return self.analyses_override
        if not self.tokens:
            return []
        out: list[Analysis] = []
        for t in self.tokens:
            if t.analysis is None:
                continue
            if t.chosen and t.chosen.headword:
                ch = t.chosen.headword
                if t.chosen.case:
                    p_str = " ".join(x for x in (t.chosen.gender, t.chosen.case, t.chosen.number) if x)
                    ch = replace(ch, parses=[p_str])
                rest = [h for h in t.analysis.headwords if h is not t.chosen.headword]
                out.append(replace(t.analysis, headwords=[ch] + rest))
            else:
                out.append(t.analysis)
        return out

    @analyses.setter
    def analyses(self, val: list[Analysis]) -> None:
        self.analyses_override = val

    def analysis_line(self) -> str:
        return " ".join(t.parse.symbols() for t in self.tokens)

    def gloss_line(self) -> str:
        return " | ".join(t.gloss or t.surface for t in self.tokens)


@dataclass
class Result:
    markdown: str
    units: list[Unit]
    seconds: float
    model_calls: int
    en_markdown: str = ""
    interlinear_markdown: str = ""

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
            num = f"Segment {u.number}" if u.number else f"Segment {i}"
            lines.append(f"### {num}\n\n> {u.source}\n\n{u.final}")
            if u.from_cache:
                lines.append("_(from cache)_")
            if u.tokens:
                lines.append("\n**Analysis:**")
                for n, t in enumerate(u.tokens, 1):
                    if not t.punct:
                        lines.append(f"- {n}. {t.surface} → {t.parse.symbols()} “{t.gloss}”")
            if u.draft and u.draft != u.current:
                lines.append(f"\nDraft: {u.draft}")
            if u.lint:
                lines.append("\n**Checker on the draft:**")
                lines.extend(f"- {'fixed' if f.severity == 'fix' else 'to fix'}: {f}" for f in u.lint)
            for r_i, r in enumerate(u.rounds, 1):
                head = f"\n**Review round {r_i}** ({r.seconds:.0f}s): "
                lines.append(head + ("no issues reported" if not r.issues else ""))
                lines.extend(f"- {iss}" for iss in r.issues)
                if r.after != r.before:
                    lines.append(f"\nRevised to: {r.after}")
                if r.lint_after:
                    lines.append("Still open after this round: " + "; ".join(r.lint_after))
            if u.open_findings:
                lines.append("\n**Unresolved:** " + "; ".join(str(f) for f in u.open_findings))
            for rej in u.rejected:
                lines.append(f"- rejected model output: {rej}")
            lines.append("")
        return "\n".join(lines)


# InterlinearResult is an alias for Result
InterlinearResult = Result


class Translator:
    def __init__(self, settings: Settings, dpd: DPD, models: ModelPool, progress: Progress | None = None,
                 use_cache: bool = True):
        self.s = settings
        self.dpd = dpd
        set_language(dpd)
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
        self._seen_spans: set[str] = set()
        self._glossed: set[str] = set()

    # -- cache ------------------------------------------------------------------------

    def _key(self, text: str, tokens: list[Token] | None = None) -> str:
        cands = "|".join(f"{t.key}:" + ",".join(p.symbols() for p in t.candidates) for t in tokens or [] if not t.punct)
        raw = "\x00".join([modern(text).strip(), Path(self.s.translate_model).name, Path(self.s.eval_model).name,
                           str(self.s.max_rounds), str(self.s.thinking), "|".join(self.s.glossary_terms), cands])
        return hashlib.sha256(raw.encode()).hexdigest()

    def save_cache(self) -> None:
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    # -- analysis ---------------------------------------------------------------------

    def analyse(self, text: str) -> list[Analysis]:
        return analyse_text(self.dpd, text)

    def _title_of_names(self, unit: Unit) -> bool:
        """A heading or cell of up to three words that are all names, honorifics, technical terms or numbers."""
        if unit.block.kind not in ("heading", "table") or unit.words > 3:
            return False
        words = unit.analyses or analyse_text(self.dpd, unit.source)
        if not words:
            return False
        for a in words:
            h = a.governing(self.s.glossary_map)
            if h is None or not (h.kind or h.stem in self.s.glossary_map):
                return False
        return True

    def _gloss_once(self, text: str) -> str:
        """A technical term or honorific is written `word` (gloss) on its first use in the document and as the plain word after (Sanskrit) or plain gloss after (Pāli)."""
        def once(m: re.Match) -> str:
            key = re.sub(r"[ṃṁoāaeīiūs]+$", "", m.group(1).lower())
            if key in self._seen_spans:
                return m.group(1) if LANGUAGE.get("code") == "sa" else m.group(2)
            self._seen_spans.add(key)
            self._glossed.add(key)
            return m.group(0)
        return re.sub(r"`([^`]+)` \(([^()]*)\)", once, text)

    def _apply(self, unit: Unit, choice: dict[int, int], gloss: dict[int, str], translation: str) -> None:
        glossary = self.s.glossary_map
        alternatives = self.s.glossary_alternatives
        for n, t in enumerate(unit.tokens, 1):
            if t.punct:
                t.gloss = t.surface
                continue
            c = choice.get(n)
            if c is not None and t.candidates and 1 <= c <= len(t.candidates):
                t.chosen = t.candidates[c - 1]
            elif t.candidates:
                t.chosen = t.candidates[0]
            t.gloss = gloss.get(n, "")
            t.chosen = reconcile_case(t.chosen, t.candidates, t.gloss)
            for stem, alts in alternatives.items():
                if stem[:-1] in (t.key or "") and t.gloss:
                    for alt in sorted(alts, key=len, reverse=True):
                        t.gloss = re.sub(r"\b" + re.escape(alt) + r"s?\b", glossary[stem], t.gloss, flags=re.I)
            h = t.chosen.headword if t.chosen else None
            is_voc = (h is None or (h.pos != "ind" and h.kind != "name")) and (
                (t.chosen and t.chosen.case == "voc") or (not t.chosen and h and bool(h.parses) and all("voc" in p for p in h.parses))
            )
            is_hon = (h and h.kind != "name" and (h.kind == "honorific" or h.stem.lower() in HONORIFICS or h.stem.lower() in HONORIFIC_MEANINGS)) or is_voc
            if is_voc and not is_hon:
                t.gloss = modern(h.stem).capitalize() if (h and h.kind == "name") else modern(t.surface)
            elif is_hon:
                form = honorific_form(h.stem if h else t.surface, t.surface, h.parses if h else [], getattr(h, "family_set", ""))
                t.gloss = _conventional(t.gloss, modern(form))
            elif h is not None:
                if h.stem in glossary:
                    t.gloss = _conventional(t.gloss, glossary[h.stem])
                elif h.kind == "name":
                    t.gloss = _conventional(t.gloss, modern(h.stem).capitalize())
                elif h.kind == "honorific":
                    t.gloss = _conventional(t.gloss, modern(honorific_form(h.stem, t.surface, h.parses, h.family_set)))
                if not t.gloss:
                    t.gloss = "(end quote)" if t.chosen and t.chosen.lemma == "iti" else (_clean_dict_gloss(h.meaning or h.meaning_2 or "?") or "?")
            elif not t.gloss:
                t.gloss = "?"
        translation = _clean_quotes(translation)
        if not translation:
            translation = " ".join(t.gloss for t in unit.tokens if not t.punct)
        fixed, findings = lint(unit.analyses, translation, glossary, alternatives=self.s.glossary_alternatives,
                               gloss_honorifics=True, glossed=self._glossed)
        fixed = format_mantra(unit.source, fixed)
        fixed = self._gloss_once(fixed)
        unit.current = unit.translation = modern(fixed) if re.search(r"[ṃ]", fixed) else fixed
        unit.draft = unit.translation
        unit.lint = findings
        unit.open_findings = [f for f in findings if f.severity == "ask"]

    # -- translation & revision --------------------------------------------------------

    def draft(self, unit: Unit, context: list[tuple[str, str]] | None = None) -> None:
        unit.tokens = analyse_tokens(self.dpd, unit.source)
        key = self._key(unit.source, unit.tokens)
        if key in self.cache:
            c = self.cache[key]
            tr_cached = c.get("translation", "")
            if tr_cached and c.get("gloss") and not tr_cached.rstrip().endswith("\\\\"):
                unit.from_cache = True
                self._apply(unit, {int(k): v for k, v in c.get("choice", {}).items()},
                            {int(k): v for k, v in c.get("gloss", {}).items()}, tr_cached)
                return

        if self._title_of_names(unit):
            unit.draft = unit.source
            unit.kept_source = True
            fixed, findings = lint(unit.analyses or analyse_text(self.dpd, unit.source),
                                   unit.draft, self.s.glossary_map, alternatives=self.s.glossary_alternatives)
            unit.current = unit.translation = fixed
            unit.lint = findings
            unit.open_findings = []
            return

        model = self.models.get("translate")
        user_prompt = prompt_for(unit.source, unit.tokens, self.s.glossary_map, context or [], initial_draft=unit.initial_draft)
        no_word_prompt = user_prompt.replace(
            'repeating the word, in this form: {"words": [{"n": 1, "word": "evaṁ", "parse": 1, "gloss": "thus"}, {"n": 2, "word": "me", "parse": 3, "gloss": "by me"}], "translation": "…"}',
            'in this form: {"words": [{"n": 1, "parse": 1, "gloss": "thus"}, {"n": 2, "parse": 3, "gloss": "by me"}], "translation": "…"}',
        )
        first_prompt = no_word_prompt if LANGUAGE.get("code") == "sa" else user_prompt
        choice: dict[int, int] = {}
        gloss: dict[int, str] = {}
        translation = ""
        for temp, use_thinking, max_tok, up in (
            (self.s.temperature, self.s.thinking, self.s.max_tokens, first_prompt),
            (0.2, False, self.s.max_tokens, no_word_prompt),
            (0.2, True, max(self.s.max_tokens, 4096), no_word_prompt),
        ):
            self.calls += 1
            messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": up}]
            reply = model.chat(messages, max_tokens=max_tok, temperature=temp, thinking=use_thinking)
            unit.raw = reply.text
            choice, gloss, translation = parse_answer(reply.text, unit.tokens)
            if not translation and not choice and reply.text.strip():
                # Fallback for models or mocks returning plain translation text
                translation = strip_wrapper(reply.text)
            elif not translation and unit.initial_draft:
                translation = unit.initial_draft
            if (gloss or not unit.tokens) and translation:
                break
        self._apply(unit, choice, gloss, translation)

    def _revise_one(self, source: str, analyses: list[Analysis], current: str, issues: list[str],
                    single_line: bool = False, markdown: bool = False,
                    context: list[tuple[str, str]] | None = None) -> str | None:
        """The translation model refines its translation addressing reviewer issues."""
        model = self.models.get("translate")
        if is_mitra_translate(model.path):
            messages = [{"role": "user", "content": translate_prompt(
                source, analyses, False, markdown, extra_terms=self.s.glossary_terms, glossary=self.s.glossary_map,
                context=context)}]
        else:
            messages = translate_messages_revision(
                source, analyses, current, issues, False, markdown,
                extra_terms=self.s.glossary_terms, glossary=self.s.glossary_map, context=context)
        max_tok = min(self.s.max_tokens, max(256, len(source.split()) * 8))
        for temp in (self.s.temperature, 0.2):
            self.calls += 1
            reply = model.chat(messages, max_tokens=max_tok, temperature=temp, thinking=self.s.thinking)
            if reply.finish_reason == "length":
                continue
            out = strip_wrapper(reply.text)
            if not out or is_degenerate(out, source) or is_meta(out):
                continue
            if single_line and "\n" in out:
                out = " ".join(out.split())
            return out
        return None

    # -- review harness loop ----------------------------------------------------------

    def review_batch(self, units: list[Unit]) -> bool:
        """One review round over a batch. Returns True if issues were found and revised."""
        model = self.models.get("review")
        seen: set[str] = set()
        analyses = []
        for u in units:
            for a in u.analyses:
                if a.key not in seen:
                    seen.add(a.key)
                    analyses.append(a)
        active_units = [u for u in units if not u.kept_source]
        if not active_units:
            return False
        segments = [(u.source, u.final) for u in active_units]
        known = {n: [str(f) for f in u.open_findings] for n, u in enumerate(active_units, 1) if u.open_findings}
        prompt = review_prompt(segments, analyses, extra_terms=self.s.glossary_terms, glossary=self.s.glossary_map, known=known)
        t0 = time.time()
        self.calls += 1
        rev_max_tokens = min(self.s.max_tokens, max(512, len(active_units) * 256))
        reply = model.chat([{"role": "system", "content": f"You are a meticulous reviewer of {LANGUAGE['name']}-to-English translations."},
                            {"role": "user", "content": prompt}],
                           max_tokens=rev_max_tokens, temperature=self.s.temperature, thinking=self.s.thinking)
        res = parse_review(reply.text, len(active_units))
        seconds = time.time() - t0
        if not res.parsed:
            for u in active_units:
                u.rejected.append("review output could not be parsed" + (" (truncated)" if reply.finish_reason == "length" else ""))
            return False
        changed = False
        still_open = False
        for n, u in enumerate(active_units, 1):
            before = u.final
            mine = [i for i in res.issues if re.search(rf"\[{n}\]|segment {n}\b", i, re.I)] or ([] if len(active_units) > 1 else res.issues)
            after = before
            if mine and not is_mitra_translate(self.models.get("translate").path):
                revised_draft = self._revise_one(
                    u.source, u.analyses, before, mine,
                    single_line=u.block.kind in ("heading", "list", "table"),
                    markdown="*" in u.source or "_" in u.source,
                    context=None
                )
                if revised_draft and revised_draft != before and not is_degenerate(revised_draft, u.source) and not is_meta(revised_draft):
                    if u.block.kind in ("heading", "list", "table") and "\n" in revised_draft:
                        revised_draft = " ".join(revised_draft.split())
                    after = revised_draft
                elif res.revised.get(n) and res.revised[n].strip() != before:
                    rev = res.revised[n].strip()
                    if not is_degenerate(rev, u.source) and not is_meta(rev):
                        if u.block.kind in ("heading", "list", "table") and "\n" in rev:
                            rev = " ".join(rev.split())
                        after = rev
            elif res.revised.get(n) and res.revised[n].strip() != before:
                rev = res.revised[n].strip()
                if not is_degenerate(rev, u.source) and not is_meta(rev):
                    if u.block.kind in ("heading", "list", "table") and "\n" in rev:
                        rev = " ".join(rev.split())
                    after = rev

            fixed, findings = lint(u.analyses, after, self.s.glossary_map, alternatives=self.s.glossary_alternatives,
                                   gloss_honorifics=True, glossed=self._glossed)
            fixed = format_mantra(u.source, fixed)
            after = modern(fixed) if re.search(r"[ṃ]", fixed) else fixed
            if after != before:
                changed = True
            u.current = u.translation = after
            u.open_findings = [f for f in findings if f.severity == "ask"]
            if u.open_findings:
                still_open = True
            u.rounds.append(Round(mine, before, after, seconds, lint_before=known.get(n, []),
                                  lint_after=[str(f) for f in u.open_findings]))
        revised = sum(1 for n, u in enumerate(active_units, 1) if res.revised.get(n, "").strip() not in ("", u.rounds[-1].before))
        self.progress(f"  reviewer: {len(res.issues)} issue(s), {revised} segment(s) revised; checker: "
                      f"{sum(len(u.open_findings) for u in active_units)} finding(s) still open")
        return changed and (bool(res.issues) or still_open)

    def _batches(self, units: list[Unit]) -> list[list[Unit]]:
        batches: list[list[Unit]] = []
        cur: list[Unit] = []
        words = 0
        for u in units:
            if u.kept_source:
                continue
            if cur and words + u.words > self.s.eval_batch_words:
                batches.append(cur)
                cur, words = [], 0
            cur.append(u)
            words += u.words
        if cur:
            batches.append(cur)
        return batches

    @staticmethod
    def _parse_numbered_translations(text: str, n_expected: int) -> dict[int, str]:
        out: dict[int, str] = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^\[?(\d+)\]?[\.:\s\-]+(.*)$", line)
            if m:
                idx = int(m.group(1))
                val = m.group(2).strip()
                if val:
                    out[idx] = val
            elif out:
                last_idx = max(out.keys())
                out[last_idx] += " " + line
        return out

    def _contextual_macro_pass(self, units: list[Unit]) -> None:
        """Initial macro pass: translate the text in context-bounded chunks to capture
        narrative flow, discourse coreference, and natural phrasing."""
        active = [u for u in units if not u.kept_source and u.source.strip()]
        if len(active) <= 1:
            return

        model = self.models.get("translate")
        if is_mitra_translate(model.path):
            return

        # Check if all active units are already cached in interlinear cache
        uncached = [u for u in active if self._key(u.source, u.tokens if u.tokens else analyse_tokens(self.dpd, u.source)) not in self.cache]
        if not uncached:
            return

        # Group into chunks of up to eval_batch_words (default 400 words)
        chunks: list[list[Unit]] = []
        cur: list[Unit] = []
        words = 0
        for u in active:
            u_words = len(u.source.split())
            if cur and words + u_words > self.s.eval_batch_words:
                chunks.append(cur)
                cur, words = [], 0
            cur.append(u)
            words += u_words
        if cur:
            chunks.append(cur)

        self.progress(f"discourse pass: generating initial contextual translation across {len(chunks)} chunk(s) …")
        for chunk in chunks:
            source_lines = [f"[{i}] {modern(u.source).strip()}" for i, u in enumerate(chunk, 1)]
            user_msg = (
                f"Translate the following {LANGUAGE['name']} text into literal, rationalist English, segment by segment.\n\n"
                f"Rules:\n"
                f"1. Literal and rationalist: render every word faithfully and drop no particle; do not assume religious or supernatural meanings.\n"
                f"2. Leave personal names, place names, and titles untranslated in their {LANGUAGE['name']} stem form (e.g. Bhagavā, Ānanda, Sāvatthī, Jetavana).\n"
                f"3. Leave vocative forms untranslated (e.g. bhikkhave, bhante, Ānanda).\n"
                f"4. Retain technical Buddhist terms: use rationalist glosses (paccaya -> cause, dukkha -> dissatisfaction, sambodhi -> full awakening, upādāna -> fuel, khandha -> collection) and never use 'enlightenment' or 'noble truth'.\n"
                f"5. Formulas: 'evaṃ me sutaṃ' / 'evaṃ mayā śrutam' must be rendered as 'Thus heard by me'.\n"
                f"6. Output one translated line per numbered segment in the form '[n] Translation text'.\n\n"
                f"{LANGUAGE['name']} text:\n" + "\n".join(source_lines)
            )
            messages = [
                {"role": "system", "content": f"You are an expert translator of classical {LANGUAGE['name']} Buddhist texts into literal English."},
                {"role": "user", "content": user_msg}
            ]
            max_tokens = min(self.s.max_tokens, max(512, len(chunk) * 128))
            self.calls += 1
            reply = model.chat(messages, max_tokens=max_tokens, temperature=self.s.temperature, thinking=self.s.thinking)
            parsed = self._parse_numbered_translations(reply.text, len(chunk))
            for i, u in enumerate(chunk, 1):
                if i in parsed and parsed[i].strip():
                    u.initial_draft = parsed[i].strip()

    # -- document rendering ------------------------------------------------------------

    def render_group(self, u: Unit, with_translation: bool = True) -> list[str]:
        num_str = f"{u.number} " if u.number else ""
        lines = [f"{num_str}{modern(u.source).strip()}  ", u.analysis_line() + "  ", u.gloss_line() + ("  " if with_translation else "")]
        if with_translation:
            lines.append(u.final)
        return lines

    def translate_markdown(self, text: str, segments: list[tuple[str, str]] | None = None,
                           interlinear: bool = False, review: bool = True) -> Result:
        t0 = time.time()
        blocks = parse_markdown(text)
        blocks_en = parse_markdown(text)
        blocks_inter = parse_markdown(text)

        units_all: list[Unit] = []
        seg_pos = 0
        para_no = 0
        recent: list[tuple[str, str]] = []

        for b in blocks:
            if not b.translatable or not HAS_LETTERS_RE.search(b.text or " ".join(c for r in b.cells for c in r)):
                continue

            if b.kind == "heading":
                para_no += 1
                u = Unit(block=b, source=b.text, masked=b.text, kept=[], number=f"0.{para_no}")
                units_all.append(u)

            elif b.kind == "list":
                para_no += 1
                u = Unit(block=b, source=b.text, masked=b.text, kept=[], number=f"L.{para_no}")
                units_all.append(u)

            elif b.kind == "table":
                for ri, row in enumerate(b.cells):
                    for ci, cell in enumerate(row):
                        if HAS_LETTERS_RE.search(cell):
                            u = Unit(block=b, cell=(ri, ci), source=cell, masked=cell, kept=[], number=f"T.{ri}.{ci}")
                            units_all.append(u)

            elif b.kind == "para":
                para_no += 1
                pieces, seg_pos, verse = units_pieces(b.text, segments, para_no, seg_pos)
                para_units = [Unit(block=b, source=txt, masked=txt, kept=[], number=num, verse=verse) for num, txt in pieces]
                units_all.extend(para_units)

        # Stage 1: Initial macro translation pass (discourse context across segments)
        self._contextual_macro_pass(units_all)

        # Stage 2: Unit-level dictionary analysis, candidate selection, and translation refinement
        for u in units_all:
            self.progress(f"[{u.number}] {u.source[:60]}{'…' if len(u.source) > 60 else ''}")
            self.draft(u, recent[-self.s.context_segments:] or None)
            recent.append((modern(u.source), u.final))

        # Stage 3: Agentic review loop
        if review and self.s.max_rounds > 0 and units_all:
            for bi, batch in enumerate(self._batches(units_all), 1):
                for r in range(1, self.s.max_rounds + 1):
                    self.progress(f"review batch {bi}, round {r} ({len(batch)} segments) …")
                    found = self.review_batch(batch)
                    if not found:
                        break

        # Re-render blocks with any revised translations from review rounds
        para_groups: dict[int, list[Unit]] = {}
        for u in units_all:
            para_groups.setdefault(id(u.block), []).append(u)

        for b, b_en, b_inter in zip(blocks, blocks_en, blocks_inter):
            bid = id(b)
            if bid not in para_groups:
                continue
            b_units = para_groups[bid]
            if b.kind in ("heading", "list") and b_units:
                b_en.translation = b_units[0].final
                b_inter.translation = b_units[0].final
            elif b.kind == "table":
                for u in b_units:
                    if u.cell is not None:
                        ri, ci = u.cell
                        b_en.cell_translations[ri][ci] = u.final
                        b_inter.cell_translations[ri][ci] = u.final
            elif b.kind == "para":
                verse = b_units[0].verse if b_units else False
                out_inter = []
                for u in b_units:
                    if out_inter:
                        out_inter.append("")
                    out_inter.extend(self.render_group(u, with_translation=not verse))
                if verse and b_units:
                    out_inter.append("")
                    out_inter.extend(f"{u.final}  " for u in b_units[:-1])
                    out_inter.append(b_units[-1].final)
                b_inter.kind = "verbatim"
                b_inter.lines = out_inter

                if verse and b_units:
                    b_en.kind = "verbatim"
                    b_en.lines = [b_en.prefix + f"{u.final}  " for u in b_units[:-1]] + [b_en.prefix + b_units[-1].final]
                elif b_units:
                    b_en.kind = "para"
                    b_en.translation = " ".join(u.final for u in b_units)

        # Save cache
        for u in units_all:
            choice_map = {str(i): (t.candidates.index(t.chosen) + 1 if t.chosen and t.candidates and t.chosen in t.candidates else 1)
                          for i, t in enumerate(u.tokens, 1) if not t.punct}
            gloss_map = {str(i): t.gloss for i, t in enumerate(u.tokens, 1) if not t.punct}
            self.cache[self._key(u.source, u.tokens)] = {
                "choice": choice_map, "gloss": gloss_map, "translation": u.final, "source": u.source
            }
        self.save_cache()

        if self.calls % getattr(self.s, "metal_cache_interval", 10) == 0:
            clear_metal_cache()

        en_md = render(blocks_en)
        inter_md = render(blocks_inter)
        return Result(
            markdown=inter_md if interlinear else en_md,
            units=units_all,
            seconds=time.time() - t0,
            model_calls=self.calls,
            en_markdown=en_md,
            interlinear_markdown=inter_md,
        )
