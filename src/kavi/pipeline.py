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
from .dpd import DPD, VERB_POS, Analysis, analyse_text, analysis_table
from .glossary import honorific_form
from .interlinear import (
    Token, analyse_tokens, backtick_curb, format_mantra,
    is_source, modern, parse_answer, prompt_for, terms_of, token_terms, reconcile_case, system_prompt, units_pieces, vocative_rule,
    _clean_quotes, _conventional,
)
from .language import LANGUAGE, set_language
from .lint import Finding, lint, HONORIFICS, HONORIFIC_MEANINGS, _clean_dict_gloss, _inside, _protected, gloss_once, term_key
from .models import (
    ModelPool, clear_metal_cache, is_mitra_translate,
    parse_review, review_prompt, strip_wrapper,
    translate_messages_revision, unusable,
)
from .segment import (
    Block, HAS_LETTERS_RE, PH_RE, parse_markdown, placeholders_ok, protect,
    render, restore, word_count,
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
    refused: set = field(default_factory=set)   # (text, issues) whose revision the gate already refused
    lint: list[Finding] = field(default_factory=list)
    open_findings: list[Finding] = field(default_factory=list)
    kept_source: bool = False
    answered: bool = False                      # the model's own answer parsed (glosses and a translation)
    raw: str = ""

    @property
    def text(self) -> str:
        return self.source

    @property
    def translation(self) -> str:
        """The latest text, with the inline markup still as placeholders (``final`` restores it)."""
        return self.current or self.draft or self.masked or self.source

    @translation.setter
    def translation(self, val: str) -> None:
        self.current = val

    @property
    def final(self) -> str:
        return restore(self.translation, self.kept) if self.kept else self.translation

    @property
    def first_pass(self) -> str:
        """The discourse draft, or the source where there is none."""
        return restore(self.initial_draft, self.kept) or self.source

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
    first_pass_en: str = ""

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



LAYOUT_MARKS_RE = re.compile(r"\s*(?:/{1,2}|\|{1,2}|‖|।{1,2}|॥)\s*$")     # the daṇḍa that closes a line or a verse
GRAMMAR_TAG_RE = re.compile(
    r"\[(?:neuter|masculine|feminine|nominative|accusative|instrumental|dative|ablative|genitive|locative|vocative|"
    r"singular|plural|dual|past|present|future|optative|imperative)[^\]]*\]|\(\s*past\s*\)", re.I)


def _untranslated_verbs(text: str, analyses: list[Analysis]) -> set[str]:
    """Finite verbs and absolutives of the source standing in the English as they are (outside backticks)."""
    out = set()
    for a in analyses:
        h = a.headwords[0] if a.headwords else None
        if h is None or h.kind or not (h.pos in VERB_POS or h.pos == "abs") or len(a.surface) < 4:
            continue
        if re.search(r"(?<![`\w])" + re.escape(a.surface) + r"(?![`\w])", text, re.I):
            out.add(a.surface.lower())
    return out


def _plain_fault(cand: str, ref: str, analyses: list[Analysis]) -> str | None:
    """What both gates refuse outright: grammatical tags, and a source verb left as it stands that ``ref`` had rendered."""
    if GRAMMAR_TAG_RE.search(cand):
        return "contains raw grammatical metadata"
    left = _untranslated_verbs(cand, analyses) - _untranslated_verbs(ref, analyses)
    return "leaves a source verb untranslated: " + ", ".join(sorted(left)) if left else None


def is_strictly_better(candidate: str, current: str, base: str, analyses: list[Analysis], glossary: dict[str, str],
                       alternatives: dict[str, list[str]] | None = None) -> tuple[bool, str]:
    """May ``candidate`` replace ``current``? Not if it carries grammatical tags or leaves a source verb
    untranslated that ``current`` had rendered, nor if the checker finds more wrong with it; with as many findings
    it must still read like the discourse draft ``base`` rather than a word-for-word calque."""
    cand = candidate.strip()
    curr = current.strip()
    if not cand:
        return False, "candidate empty"
    if cand == curr:
        return False, "identical to current"
    if (why := _plain_fault(cand, curr, analyses)):
        return False, why

    _, findings_cand = lint(analyses, cand, glossary, apply=False, alternatives=alternatives)
    _, findings_curr = lint(analyses, curr, glossary, apply=False, alternatives=alternatives)
    if len(findings_cand) < len(findings_curr):
        return True, f"resolved {len(findings_curr) - len(findings_cand)} linter finding(s)"
    if len(findings_cand) > len(findings_curr):
        return False, "candidate has more findings than current"

    from .evaluate import word_f1
    f1_cand = word_f1(cand, base) if base else 100.0
    min_f1 = 15.0 if len(base.split()) <= 10 else 25.0
    if f1_cand >= min_f1:
        return True, "valid refinement preserving base sentence structure"
    return False, f"diverged too far from base English into word-salad (f1={f1_cand:.1f} < {min_f1})"


def grounded_fault(candidate: str, draft: str, unit: Unit, glossary: dict[str, str],
                   alternatives: dict[str, list[str]] | None = None) -> str | None:
    """Why the sentence grounded on the dictionary's parses (Stage 2) may not replace the discourse draft (Stage 1);
    None when it may. The grounded sentence is the one the word glosses belong to, so it stands unless something is
    plainly wrong with it: it is not measured by its likeness to the ungrounded draft, and what the checker mends by
    itself (an honorific in English, a glossary alternative) is mended in both before they are compared."""
    cand = candidate.strip()
    if unusable(cand, unit.source):
        return "no usable sentence"
    analyses = unit.analyses
    if (why := _plain_fault(cand, draft, analyses)):
        return why
    if unit.kept and not placeholders_ok(cand, unit.masked) and placeholders_ok(draft, unit.masked):
        return "a placeholder was lost or invented"

    def open_of(text: str) -> int:
        return sum(1 for f in lint(analyses, text, glossary, alternatives=alternatives)[1] if f.severity == "ask")

    more = open_of(cand) - open_of(draft)
    return f"{more} more open finding(s) than the draft after the checker's fixes" if more > 0 else None


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
            except (ValueError, OSError):        # truncated or unreadable: start afresh
                self.cache = {}
        self._seen_spans: set[str] = set()
        self._dirty = False
        self._translator_released = False
        self._glossed: set[str] = set()

    # -- cache ------------------------------------------------------------------------

    def _key(self, text: str, tokens: list[Token] | None = None) -> str:
        cands = "|".join(f"{t.key}:" + ",".join(p.symbols() for p in t.candidates) for t in tokens or [] if not t.punct)
        raw = "\x00".join([modern(text).strip(), Path(self.s.translate_model).name, Path(self.s.eval_model).name,
                           str(self.s.max_rounds), str(self.s.thinking), "|".join(self.s.glossary_terms), cands])
        return hashlib.sha256(raw.encode()).hexdigest()

    def _remember(self, u: Unit) -> None:
        """Cache a unit whose answer the model itself gave: not a fallback, a title kept as source or a cache hit."""
        if not u.answered:
            return
        choice_map = {str(i): (t.candidates.index(t.chosen) + 1 if t.chosen and t.candidates and t.chosen in t.candidates else 1)
                      for i, t in enumerate(u.tokens, 1) if not t.punct}
        gloss_map = {str(i): t.gloss for i, t in enumerate(u.tokens, 1) if not t.punct}
        key = self._key(u.source, u.tokens)
        entry = {"choice": choice_map, "gloss": gloss_map, "translation": u.translation, "source": u.source}
        if self.cache.get(key) != entry:
            self.cache[key] = entry
            self._dirty = True

    def save_cache(self) -> None:
        if self.cache_path and self._dirty:              # nothing new: the file is left as it is
            self._dirty = False
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.cache_path)

    # -- analysis ---------------------------------------------------------------------

    def analyse(self, text: str) -> list[Analysis]:
        return analyse_text(self.dpd, text)

    def _translatable(self, text: str) -> bool:
        """Letters outside the inline markup, in the source language."""
        bare = PH_RE.sub(" ", protect(text)[0])
        return bool(HAS_LETTERS_RE.search(bare)) and is_source(self.dpd, bare)

    @staticmethod
    def _unit(block: Block, text: str, number: str, **kw) -> Unit:
        masked, kept = protect(text)                     # links, footnote marks, tags and code spans as %%n%%
        return Unit(block=block, source=text, masked=masked, kept=kept, number=number, **kw)

    @staticmethod
    def _fit_placeholders(unit: Unit, text: str) -> str:
        """A translation that lost, repeated or invented a placeholder: the strays go and the missing ones are put
        at the end, so that no link or footnote mark of the source is dropped from the page."""
        if not unit.kept or placeholders_ok(text, unit.masked):
            return text
        if not PH_RE.search(text) and all(k in text for k in unit.kept):
            return text                                  # the markup itself stands in the text
        seen: set[str] = set()

        def once(m: re.Match) -> str:
            n = m.group(1)
            if int(n) >= len(unit.kept) or n in seen:
                return ""
            seen.add(n)
            return f"%%{n}%%"

        text = re.sub(r"\s{2,}", " ", PH_RE.sub(once, text)).strip()
        missing = [f"%%{i}%%" for i in range(len(unit.kept)) if str(i) not in seen]
        return (text + " " + " ".join(missing)).strip() if missing else text

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
        text = gloss_once(text, self._seen_spans)
        self._glossed |= self._seen_spans
        return text

    def _enforce_first_use_conventions(self, units: list[Unit]) -> None:
        """Deterministically enforces the first-use convention across the entire document:
        First occurrence in text: `term` (gloss)
        Subsequent occurrences: plain term (Sanskrit) or plain gloss (Pāli)."""
        seen: set[str] = set()
        glossary = self.s.glossary_map
        is_sa = LANGUAGE.get("code") == "sa"

        for u in units:
            if u.kept_source or not u.translation:
                continue
            text = u.translation

            # Preserve italicized mantras from internal term wrapping
            mantras = []
            def save_mantra(m: re.Match) -> str:
                mantras.append(m.group(0))
                return f"__MANTRA_{len(mantras)-1}__"
            text = re.sub(r"\*[^*]+\*", save_mantra, text)

            # 1. the spans already written: the first of each term stays
            text = gloss_once(text, seen)

            # 2. For any glossary term present in this unit's source that hasn't been glossed yet
            for a in u.analyses:
                h = a.governing(glossary)
                if not h or h.stem not in glossary:
                    continue
                stem = h.stem
                gloss = glossary[stem]
                if not gloss:
                    continue                         # a context-dependent term (dhamma): left alone, as in lint
                key = term_key(stem)
                if key in seen:
                    continue
                # the bare term or the bare gloss, as a whole word outside any existing `term` (gloss) span
                spans = _protected(text)
                for pat, shown in ((stem, None), (gloss, stem)):
                    rx = re.compile(r"(?<![`\w-])" + re.escape(pat) + r"(?![`\w-])(?!\s*\()", re.I)
                    m = next((mm for mm in rx.finditer(text) if not _inside(mm.start(), spans)), None)
                    if m:
                        wrapped = f"`{shown or m.group(0)}` ({gloss if shown is None else m.group(0)})"
                        text = text[:m.start()] + wrapped + text[m.end():]
                        seen.add(key)
                        break

            for idx, m_text in enumerate(mantras):
                text = text.replace(f"__MANTRA_{idx}__", m_text)

            u.current = u.translation = text

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
            terms = token_terms(t) if t.gloss else set()
            for stem, alts in alternatives.items():
                if stem in terms:
                    for alt in sorted(alts, key=len, reverse=True):
                        t.gloss = re.sub(r"\b" + re.escape(alt) + r"s?\b", glossary[stem], t.gloss, flags=re.I)
            h = t.chosen.headword if t.chosen else None
            is_voc = (h is None or (h.pos != "ind" and h.kind != "name")) and (
                (t.chosen and t.chosen.case == "voc") or (not t.chosen and h and bool(h.parses) and all("voc" in p for p in h.parses))
            )
            is_hon = (h and h.kind != "name" and (h.kind == "honorific" or h.stem.lower() in HONORIFICS or h.stem.lower() in HONORIFIC_MEANINGS)) or is_voc
            ruled = h is not None and not is_voc and LANGUAGE.get("code") != "sa" and bool(glossary.get(h.stem))
            if ruled:                                    # samaṇa "wanderer": the ruling, as the checker has it
                t.gloss = _conventional(t.gloss, glossary[h.stem])
            elif is_hon:
                form = honorific_form(h.stem if h else t.surface, t.surface, h.parses if h else [], getattr(h, "family_set", ""))
                t.gloss = _conventional(t.gloss, modern(form))
            elif h is not None:
                if glossary.get(h.stem):
                    t.gloss = _conventional(t.gloss, glossary[h.stem])
                elif h.kind == "name":
                    t.gloss = _conventional(t.gloss, modern(h.stem).capitalize())
                if not t.gloss:
                    t.gloss = "(end quote)" if t.chosen and t.chosen.lemma == "iti" else (_clean_dict_gloss(h.meaning or h.meaning_2 or "?") or "?")
            elif not t.gloss:
                t.gloss = "?"
        translation = _clean_quotes(translation)
        if not translation:
            translation = unit.initial_draft or " ".join(t.gloss for t in unit.tokens if not t.punct)
        elif unit.initial_draft and not unit.from_cache:     # a cached entry is the reviewed text: it stands
            reason = grounded_fault(translation, unit.initial_draft, unit, glossary, alternatives)
            if reason:
                unit.rejected.append(f"grounded sentence set aside for the discourse draft ({reason}): {translation}")
                translation = unit.initial_draft
        fixed, findings = lint(unit.analyses, translation, glossary, alternatives=self.s.glossary_alternatives,
                               glossed=self._glossed)
        fixed = format_mantra(unit.source, fixed)
        fixed = self._fit_placeholders(unit, self._gloss_once(fixed))
        unit.current = unit.translation = modern(fixed)
        unit.draft = unit.translation
        unit.lint = findings
        unit.open_findings = [f for f in findings if f.severity == "ask"]

    # -- translation & revision --------------------------------------------------------

    def draft(self, unit: Unit, context: list[tuple[str, str]] | None = None) -> None:
        if not unit.tokens:
            unit.tokens = analyse_tokens(self.dpd, unit.masked or unit.source)
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
            unit.draft = unit.masked or unit.source
            unit.kept_source = True
            fixed, findings = lint(unit.analyses or analyse_text(self.dpd, unit.source),
                                   unit.draft, self.s.glossary_map, alternatives=self.s.glossary_alternatives)
            unit.current = unit.translation = fixed
            unit.lint = findings
            unit.open_findings = []
            return

        model = self.models.get("translate")
        whole = protect(unit.block.text)[0] if unit.verse else ""     # a verse line is read with the rest of its verse
        user_prompt = prompt_for(unit.masked or unit.source, unit.tokens, self.s.glossary_map, context or [],
                                 initial_draft=unit.initial_draft, whole=whole)
        no_word_prompt = user_prompt.replace(
            'repeating the word, in this form: {"words": [{"n": 1, "word": "evaṁ", "parse": 1, "gloss": "thus"}, {"n": 2, "word": "me", "parse": 3, "gloss": "by me"}], "translation": "…"}',
            'in this form: {"words": [{"n": 1, "parse": 1, "gloss": "thus"}, {"n": 2, "parse": 3, "gloss": "by me"}], "translation": "…"}',
        )
        first_prompt = no_word_prompt if LANGUAGE.get("code") == "sa" else user_prompt
        choice: dict[int, int] = {}
        gloss: dict[int, str] = {}
        translation = ""
        # a word's JSON entry runs to some thirty tokens: the budget follows the sentence, and doubles after a cut
        budget = max(self.s.max_tokens, 30 * sum(1 for t in unit.tokens if not t.punct) + 256)
        for temp, use_thinking, up in (
            (self.s.temperature, self.s.thinking, first_prompt),
            (0.2, False, no_word_prompt),
            (0.2, True, no_word_prompt),
        ):
            self.calls += 1
            messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": up}]
            reply = model.chat(messages, max_tokens=budget + (2048 if use_thinking else 0), temperature=temp, thinking=use_thinking)
            unit.raw = reply.text
            choice, gloss, translation = parse_answer(reply.text, unit.tokens)
            unit.answered = bool(gloss and translation)
            plain = strip_wrapper(reply.text)
            if (not translation and not choice and plain and "{" not in plain and reply.finish_reason != "length"
                    and not unusable(plain, unit.source)):
                translation = plain                      # a model that answers with the translation alone
            elif not translation and unit.initial_draft:
                translation = unit.initial_draft
            if (gloss or not unit.tokens) and translation:
                break
            if reply.finish_reason == "length":
                budget *= 2
        self._apply(unit, choice, gloss, translation)

    def _revise_one(self, source: str, analyses: list[Analysis], current: str, issues: list[str],
                    single_line: bool = False, markdown: bool = False) -> str | None:
        """The translation model refines its translation addressing reviewer issues."""
        model = self.models.get("translate")
        messages = translate_messages_revision(
            source, analyses, current, issues, bool(PH_RE.search(source)), markdown,
            extra_terms=self.s.glossary_terms, glossary=self.s.glossary_map)
        max_tok = max(256, len(source.split()) * 12) + (1024 if self.s.thinking else 0)
        for temp in (self.s.temperature, 0.2):
            self.calls += 1
            reply = model.chat(messages, max_tokens=max_tok, temperature=temp, thinking=self.s.thinking)
            if reply.finish_reason == "length":
                max_tok *= 2                             # the same budget would only be cut again
                continue
            out = strip_wrapper(reply.text)
            if unusable(out, source):
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
        segments = [(u.masked or u.source, u.translation) for u in active_units]
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
            before = u.translation
            mine = [i for i in res.issues if re.search(rf"\[{n}\]|segment {n}\b", i, re.I)] or ([] if len(active_units) > 1 else res.issues)
            after = before
            single = u.block.kind in ("heading", "list", "table")
            tried = (before, tuple(mine))
            if (mine and tried not in u.refused and not self._translator_released
                    and not is_mitra_translate(self.models.get("translate").path)):
                after = self._revise_one(u.masked or u.source, u.analyses, before, mine, single_line=single,
                                         markdown="*" in u.source or "_" in u.source) or before
            if after == before and res.revised.get(n, "").strip() not in ("", before):
                rev = res.revised[n].strip()             # the reviewer's own line, when the translator gave none
                if not unusable(rev, u.source):
                    after = " ".join(rev.split()) if single else rev

            # the checker's fixes first, then one decision on the text that would go on the page
            fixed, findings = lint(u.analyses, after, self.s.glossary_map, alternatives=self.s.glossary_alternatives,
                                   glossed=self._glossed)
            fixed = format_mantra(u.source, fixed)
            final_cand = modern(fixed)
            if final_cand != before:
                is_better, reason = is_strictly_better(final_cand, before, u.initial_draft or before, u.analyses,
                                                       self.s.glossary_map, self.s.glossary_alternatives)
                if is_better and u.kept and not placeholders_ok(final_cand, u.masked):
                    is_better, reason = False, "a placeholder was lost or invented"
                if is_better:
                    after = final_cand
                    changed = True
                else:
                    u.rejected.append(f"revision rejected ({reason}): {final_cand}")
                    u.refused.add(tried)                 # the same text and issues would be refused again
                    after = before
                    findings = list(u.open_findings)       # the text did not change: nor do its open findings
            else:
                after = before

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

    def _batches(self, units: list[Unit], reviewable: bool = True) -> list[list[Unit]]:
        """Runs of units up to eval_batch_words source words; for review, without the titles kept as source and
        the units served from the cache (a cached entry is already the reviewed text)."""
        batches: list[list[Unit]] = []
        cur: list[Unit] = []
        words = 0
        for u in units:
            if reviewable and (u.kept_source or u.from_cache):
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
    def _parse_numbered_translations(text: str) -> dict[int, str]:
        out: dict[int, str] = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^\[?(\d+)\]?[\.:\s\-]+(.*)$", line)
            if m:
                idx = int(m.group(1))
                val = re.sub(r"[\s|‖/]+$", "", m.group(2).strip()).strip()
                if val and idx not in out:               # a number given twice: the first stands (the second is an echo)
                    out[idx] = val
            elif out:
                last_idx = max(out.keys())
                cleaned = re.sub(r"[\s|‖]+$", "", line).strip()
                if cleaned:
                    out[last_idx] += " " + cleaned
        return out

    def _term_rules(self, chunk: list[Unit]) -> str:
        """The glossary's rulings for the terms of this chunk: "stem -> gloss (never 'alternative')"."""
        glossary, alternatives = self.s.glossary_map, self.s.glossary_alternatives
        present = terms_of(t for u in chunk for t in u.tokens)
        out = []
        for stem, gloss in glossary.items():
            if gloss and stem in present:
                never = ", ".join(f"'{x}'" for x in alternatives.get(stem, [])[:3])
                out.append(f"{modern(stem)} -> {gloss}" + (f" (never {never})" if never else ""))
        return "; ".join(out)

    @staticmethod
    def _kept_words(chunk: list[Unit]) -> dict[str, str]:
        """The names, titles and honorifics of this chunk, stem -> as it is to be written: what the draft must leave
        as it is. A word the dictionary knows as a name but also reads as an ordinary word is left out (it may be a
        description here), and so is a stem that is only a homonym behind the first reading. A heading names the
        text and takes its English in parentheses, so it contributes nothing."""
        out: dict[str, str] = {}
        for u in chunk:
            if u.block.kind == "heading":
                continue
            for t in u.tokens:
                first = t.candidates[0] if t.candidates else None
                h = first.headword if first else None
                if h is None:
                    continue
                proper = h.kind == "name" or t.surface[:1].isupper()      # Rāhulabhadra: one name, not rāhula + bhadra
                stems = {h.stem} if proper else {h.stem} | {m.replace("ṁ", "ṃ") for m in first.members}
                for stem in sorted(stems):
                    if stem in HONORIFICS:
                        out.setdefault(stem, modern(honorific_form(stem, stem, [], h.family_set)))
                    elif t.only_names:
                        out.setdefault(stem, modern(stem.capitalize()))
        return out

    @staticmethod
    def _address_words(chunk: list[Unit], kept: dict[str, str]) -> list[str]:
        """The words that can be words of address, which a model seldom finds for itself: the lexicon's own first
        reading is a vocative singular, or the form allows a vocative singular and no nominative and no reading as a
        verb, a pronoun or an indeclinable. Left out: names and titles (they stay bare), headings, and a locative that
        agrees with the noun beside it."""
        def locative(t: Token, first: bool = False) -> bool:
            return any(p.case == "loc" and p.number == "sg" for p in (t.candidates[:1] if first else t.candidates))

        out: dict[str, None] = {}
        for u in chunk:
            if u.block.kind == "heading":                # a title names; it addresses no one
                continue
            words = [t for t in u.tokens if not t.punct]
            for n, t in enumerate(words):
                c = t.candidates
                if not (len(t.surface) >= 4 and c and c[0].kind == "noun"):
                    continue
                if t.only_names or (c[0].headword is not None and c[0].headword.stem in kept):
                    continue
                if locative(t) and any(locative(x, first=True) for x in words[max(0, n - 1):n] + words[n + 1:n + 2]):
                    continue                             # āśaye śuddhe: a locative with the noun it agrees with
                first = c[0].case == "voc" and c[0].number == "sg"          # the lexicon's own first reading (kalyāṇi)
                by_form = (not any(p.kind in ("verb", "ind", "affix", "pron") for p in c)
                           and any(p.case == "voc" and p.number == "sg" for p in c)
                           and not any(p.case == "nom" and p.number in ("sg", "pl") for p in c))
                if first or by_form:
                    out[modern(t.surface)] = None
        return list(out)

    def _contextual_macro_pass(self, units: list[Unit], force: bool = False) -> None:
        """Initial macro pass: translate the text in context-bounded chunks to capture narrative flow, discourse
        coreference and natural phrasing. Sentences whose Stage 2 answer is cached are not redrafted unless ``force``
        (for work on this prompt, whose output is wanted for every unit)."""
        active = [u for u in units if not u.kept_source and u.source.strip()]
        if len(active) <= 1:
            return
        for u in active:                                 # analysed once: draft() reuses the tokens
            if not u.tokens:
                u.tokens = analyse_tokens(self.dpd, u.masked or u.source)
        uncached = {id(u) for u in active if force or self._key(u.source, u.tokens) not in self.cache}
        if not uncached:
            return
        paths = getattr(self.models, "paths", None)      # the path decides, without loading the model for it
        if is_mitra_translate(paths["translate"] if paths else self.models.get("translate").path):
            return
        model = self.models.get("translate")
        chunks = [c for c in self._batches(active, reviewable=False) if any(id(u) in uncached for u in c)]

        self.progress(f"discourse pass: generating initial contextual translation across {len(chunks)} chunk(s) …")
        is_sa = LANGUAGE.get("code") == "sa"
        lang_name = LANGUAGE['name']
        name_examples = "Bhagavān, Śāriputra, Śrāvastī" if is_sa else "Bhagavā, Ānanda, Sāvatthī, Jetavana"
        voc_examples = "Śāriputra, bhagavan, bhikṣavaḥ" if is_sa else "bhikkhave, bhante, Ānanda"
        idioms = ("   - 'yāvat' closing an abbreviated list means 'and so forth up to'.\n"
                  "   - Correlatives 'yad ... tad' mean 'whatever ... that'.\n" if is_sa else "")
        avagraha = (" An apostrophe at the start of a word stands for an elided a-: read 'x as ax, which often makes the word "
                    "a negative.") if is_sa else ""

        for chunk in chunks:
            opens = [True] + [a.block is not b.block for a, b in zip(chunk, chunk[1:])]   # a paragraph or a verse begins
            source_lines = []
            for i, (u, new) in enumerate(zip(chunk, opens), 1):    # a blank line between paragraphs and between verses
                if new and i > 1:
                    source_lines.append("")
                source_lines.append(f"[{i}] {LAYOUT_MARKS_RE.sub('', modern(u.masked or u.source).strip())}")
            term_rules = self._term_rules(chunk)
            kept = self._kept_words(chunk)
            bare = list(dict.fromkeys(kept.values()))
            address = self._address_words(chunk, kept)
            kept_rule = (" These words of this text are names and titles: write each bare, exactly as shown (the plural with an "
                         "English -s), wherever it occurs and in whatever case form, never in backticks and never followed by "
                         f"English in parentheses: {', '.join(bare)}.") if bare else ""
            address_rule = (" By their form these words of this text can be words of address (the same form may be another case: "
                            "the sentence decides); where one addresses someone and is not a name or title, it is written "
                            f"`word` (English) with the word exactly as shown here: {', '.join(address)}."
                            " Only a word of this list may be written in backticks, and only where it addresses someone; a word "
                            "that is not on the list is never in backticks, even when it describes the one addressed.") if address else ""
            terms_clause = f": {term_rules}." if term_rules else "."
            rules = [
                "Strictly literal and rationalist: Render every word faithfully and drop no particle; maintain fluent English syntax without theological, devotional, or supernatural idioms.",
                f"Names and Text Titles: Leave personal names, place names, and honorific stems untranslated (e.g. {name_examples}).{kept_rule}"
                " The title of the text remains untranslated, with its English translation in parentheses on its first occurrence only; later occurrences are the title alone.",
                f"Vocatives: Leave names, titles and customary forms of address in the vocative untranslated, without Victorian titles or parentheticals (e.g. {voc_examples}). "
                f"{vocative_rule()}. {backtick_curb()}.{address_rule}",
                f"Doctrinal Terms: Use the glossary's renderings{terms_clause} Never use 'enlightenment' or 'noble truth'."
                " Before using a glossary rendering, look at the word's case: a glossary word standing alone in the instrumental or ablative beside a verb"
                " is normally an adverb of manner, and is translated as an English adverb."
                " A glossary term is written as its English rendering only, never left untranslated.",
                "Formulas and Canonical Idioms:\n"
                "   - 'evaṃ me sutaṃ' / 'evaṃ mayā śrutam' must be rendered as 'Thus heard by me'.\n"
                + idioms +
                "   - Mantras: italicise the incantation, followed by its English meaning in parentheses: *mantra* (translation).",
                "Punctuation: Use standard English punctuation (periods, commas, semicolons); a paragraph or verse begins with a capital and ends with a full stop. The marks /, //, | and || are layout, not text: never write them.",
                "Format: Output one translated line per numbered segment in the form '[n] Translation text'. Each number appears exactly once, and its line is English only, never the source words copied.",
                "Construing: Numbered segments with no blank line between them are one paragraph or one verse, and their words construe together."
                " Before writing it, find its finite verb and its subject: a word in the accusative is never the subject, an adjective takes the case of the noun it agrees with (not of the nearest noun), and a negation negates the verb of its own clause."
                " Then give each numbered segment the English of its own words: add no noun or clause that has no word in that segment, and leave out no word of it."
                + avagraha,
                "Placeholders: reproduce every %%number%% marker of a segment exactly, once, in its translation.",
            ]
            user_msg = (
                f"Translate the following {lang_name} text into literal, rationalist English, segment by segment.\n\nRules:\n"
                + "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
                + f"\n\n{lang_name} text:\n" + "\n".join(source_lines)
            )
            messages = [
                {"role": "system", "content": f"You are an expert translator of classical {lang_name} Buddhist texts into literal English."},
                {"role": "user", "content": user_msg}
            ]
            # English runs to about six tokens a source word (long compounds, diacritics), plus the numbering
            need = 6 * sum(u.words for u in chunk) + 32 * len(chunk) + 128
            max_tokens = max(512, min(need, max(self.s.max_tokens, 4096)))
            self.calls += 1
            reply = model.chat(messages, max_tokens=max_tokens, temperature=self.s.temperature, thinking=self.s.thinking)
            parsed = self._parse_numbered_translations(reply.text)
            if reply.finish_reason == "length" and parsed:
                parsed.pop(max(parsed))                  # the last line was cut off: no draft is better than half of one
            gloss_after_name = re.compile(r"`?\b(" + "|".join(map(re.escape, bare)) + r")(s?)`?\s*\([^()]*\)", re.I) if bare else None
            for i, (u, new) in enumerate(zip(chunk, opens), 1):
                if not parsed.get(i):
                    continue
                text = parsed[i]
                if gloss_after_name:                     # a name or title takes no explanation in parentheses
                    text = gloss_after_name.sub(r"\1\2", text)
                if new:
                    text = text[:1].upper() + text[1:]   # a paragraph or verse begins with a capital
                u.initial_draft = self._fit_placeholders(u, text)

    # -- document rendering ------------------------------------------------------------

    def render_group(self, u: Unit, with_translation: bool = True) -> list[str]:
        num_str = f"{u.number} " if u.number else ""
        lines = [f"{num_str}{modern(u.source).strip()}  ", u.analysis_line() + "  ", u.gloss_line() + ("  " if with_translation else "")]
        if with_translation:
            lines.append(u.final)
        return lines

    def translate_markdown(self, text: str, segments: list[tuple[str, str]] | None = None,
                           interlinear: bool = False, review: bool = True, stage1_only: bool = False) -> Result:
        t0 = time.time()
        calls0 = self.calls
        blocks = parse_markdown(text)
        blocks_en = parse_markdown(text)
        blocks_inter = parse_markdown(text)
        blocks_fp = parse_markdown(text)

        units_all: list[Unit] = []
        self._seen_spans.clear()
        self._glossed.clear()
        seg_pos = 0
        para_no = 0
        other_no = 0
        recent: list[tuple[str, str]] = []

        for b in blocks:
            if not b.translatable or not HAS_LETTERS_RE.search(b.text or " ".join(c for r in b.cells for c in r)):
                continue

            if b.kind in ("heading", "list"):
                if not self._translatable(b.text):
                    continue
                other_no += 1                            # headings and list items do not use up paragraph numbers
                units_all.append(self._unit(b, b.text, f"{'0' if b.kind == 'heading' else 'L'}.{other_no}"))

            elif b.kind == "table":
                for ri, row in enumerate(b.cells):
                    for ci, cell in enumerate(row):
                        if self._translatable(cell):
                            units_all.append(self._unit(b, cell, f"T.{ri}.{ci}", cell=(ri, ci)))

            elif b.kind == "para":
                if not self._translatable(b.text):
                    continue                             # English prose on a mixed page stays as it is
                para_no += 1
                pieces, seg_pos, verse = units_pieces(b.text, segments, para_no, seg_pos)
                units_all.extend(self._unit(b, txt, num, verse=verse) for num, txt in pieces)

        # two different models do not both fit a 64 GB machine: the reviewer goes while the translator works
        two_models = self.s.release_translator and self.s.translate_model != self.s.eval_model
        self._translator_released = False
        if two_models:
            self.models.release("review")

        # Stage 1: Initial macro translation pass (discourse context across segments)
        self._contextual_macro_pass(units_all, force=stage1_only)

        # Stage 2: Unit-level dictionary analysis, candidate selection, and translation refinement
        staged = [] if stage1_only else units_all         # the discourse draft alone is wanted, as the model gave it
        interval = max(1, self.s.metal_cache_interval)
        for n, u in enumerate(staged, 1):
            self.progress(f"[{u.number}] {u.source[:60]}{'…' if len(u.source) > 60 else ''}")
            self.draft(u, recent[-self.s.context_segments:] if self.s.context_segments > 0 else None)
            recent.append((modern(u.source), u.final))
            self._remember(u)
            if n % interval == 0:                        # an interrupted run keeps what it has done
                self.save_cache()
                clear_metal_cache()

        # Stage 3: Agentic review loop
        if review and self.s.max_rounds > 0 and staged:
            if two_models:                               # and the translator goes before the review: the reviewer's own
                self.models.release("translate")         # revised lines are then used, with no call back to the translator
                self._translator_released = True
            for bi, batch in enumerate(self._batches(staged), 1):
                for r in range(1, self.s.max_rounds + 1):
                    self.progress(f"review batch {bi}, round {r} ({len(batch)} segments) …")
                    found = self.review_batch(batch)
                    if not found:
                        break

        # Deterministically enforce technical term first-use formatting across the document
        self._enforce_first_use_conventions(staged)

        # Re-render blocks with any revised translations from review rounds
        para_groups: dict[int, list[Unit]] = {}
        for u in units_all:
            para_groups.setdefault(id(u.block), []).append(u)

        for b, b_en, b_inter, b_fp in zip(blocks, blocks_en, blocks_inter, blocks_fp):
            bid = id(b)
            if bid not in para_groups:
                continue
            b_units = para_groups[bid]
            if b.kind in ("heading", "list") and b_units:
                b_en.translation = b_units[0].final
                b_inter.translation = b_units[0].final
                b_fp.translation = b_units[0].first_pass
            elif b.kind == "table":
                for tb in (b_en, b_inter, b_fp):
                    tb.cell_translations = [[None] * len(r) for r in b.cells]
                for u in b_units:
                    if u.cell is not None:
                        ri, ci = u.cell
                        b_en.cell_translations[ri][ci] = u.final
                        b_inter.cell_translations[ri][ci] = u.final
                        b_fp.cell_translations[ri][ci] = u.first_pass
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
                    b_fp.kind = "verbatim"
                    b_fp.lines = [b_fp.prefix + f"{u.first_pass}  " for u in b_units[:-1]] + [b_fp.prefix + b_units[-1].first_pass]
                elif b_units:
                    b_en.kind = "para"
                    b_en.translation = " ".join(u.final for u in b_units)
                    b_fp.kind = "para"
                    b_fp.translation = " ".join(u.first_pass for u in b_units)

        for u in staged:                                 # the reviewed text replaces the draft's entry
            self._remember(u)
        self.save_cache()
        clear_metal_cache()

        en_md = render(blocks_en)
        inter_md = render(blocks_inter)
        fp_en_md = render(blocks_fp)
        return Result(
            markdown=fp_en_md if stage1_only else (inter_md if interlinear else en_md),
            units=units_all,
            seconds=time.time() - t0,
            model_calls=self.calls - calls0,
            en_markdown=en_md,
            interlinear_markdown=inter_md,
            first_pass_en=fp_en_md,
        )
