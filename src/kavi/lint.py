"""Mechanical checks on a draft translation, from the DPD analysis.

A 9B reviewer waves a draft through unless it is told exactly what to look at, so the deterministic part of the
review is done here. Every finding names the Pāḷi word, what is wrong and the exact fix; the fixes that are pure
string edits are applied directly, the rest are handed to the reviewer as instructions.

* **names** must appear untranslated in their stem form: if the stem is absent and one of the DPD's English
  meanings (or the literal meaning, "deer park") is present instead, that phrase is replaced by the stem;
* **honorifics** must appear as they stand in the text (bhagavā, bhikkhave): an English rendering found in
  their place (the Blessed One, monks) is replaced by the Pāḷi word;
* **technical terms** (glossary or DPD sets) must appear on first use as `word` (gloss): a bare English gloss
  is rewritten into that form; the reviewer is asked when no gloss is found;
* **particles** (kho, pana, eva, hi, ca, vā, pi, iti …) must be rendered: if none of a particle's DPD meanings
  occurs in the English, the reviewer is asked to add one;
* **finite verbs** carry their tense: a present-tense verb whose English shows only past forms is flagged.

Each finding is a :class:`Finding` with ``severity`` "fix" (applied here) or "ask" (for the reviewer).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .dpd import VERB_POS, Analysis, Headword
from .glossary import honorific_form, term_form

PARTICLES = {"kho", "pana", "eva", "hi", "ca", "vā", "pi", "api", "iti", "nu", "tu", "kira", "atha", "khalu",
             "ce", "sace", "yadi", "tāva", "yāva", "puna", "idha", "tattha", "tatra", "evaṃ", "tathā", "yathā"}
PARTICLE_ENGLISH = {"iti": ["thus", "so", "saying", '"', "“", "’", "'", ":"], "ca": ["and", "also", "too"], "pi": ["also", "too", "even", "and"],
                    "ce": ["if"], "sace": ["if"], "yadi": ["if", "whether"], "tāva": ["so long", "first", "so far", "still"],
                    "yāva": ["as long as", "as far as", "until", "up to", "so"], "puna": ["again", "further", "moreover"],
                    "evaṃ": ["thus", "so", "in this way", "like this"], "tathā": ["so", "thus", "likewise", "in that way"],
                    "yathā": ["as", "just as", "how", "like"], "idha": ["here", "in this"], "tattha": ["there", "in that"],
                    "tatra": ["there", "in that"],
                    "api": ["also", "too", "even"], "vā": ["or", "either"], "eva": ["only", "just", "indeed", "very", "itself", "himself"],
                    "hi": ["for", "indeed", "because", "truly"], "kho": ["indeed", "surely", "certainly", "truly", "then", "now"],
                    "pana": ["but", "however", "moreover", "and", "now", "then", "further"], "nu": ["?"], "tu": ["but", "however"],
                    "kira": ["it is said", "they say", "apparently", "reportedly"], "atha": ["then", "and then", "now", "but"]}
ARTICLE_RE = r"(?:\b(?:the|a|an|this|that|these|those)\s+)?"


@dataclass
class Finding:
    word: str
    problem: str
    fix: str
    severity: str = "ask"        # 'fix' when applied here, 'ask' when the reviewer must act

    def __str__(self) -> str:
        return f"'{self.word}': {self.problem} — {self.fix}"


def english_variants(h: Headword, siblings: list[Headword] | None = None) -> list[str]:
    """English phrases a model is likely to have used for this headword (and its homonyms of the same kind:
    bhagavant the adjective "fortunate" and bhagavant the noun "Blessed One" are one word to the model)."""
    out = []
    for hw in [h] + [x for x in (siblings or []) if x is not h and x.kind == h.kind and x.stem[:5] == h.stem[:5]]:
        out.extend(_variants_of(hw))
    return sorted(set(out), key=len, reverse=True)


def _variants_of(h: Headword) -> list[str]:
    out = []
    for m in re.split(r"[;,]", h.meaning or ""):
        m = m.strip()
        if not m or m.lower().startswith(("name of", "epithet of", "(", "lit.")) or len(m) < 2:
            continue
        m = re.sub(r"\s*\([^)]*\)", "", m).strip()
        if m:
            out.append(m)
    if h.meaning_lit:
        out.append(re.sub(r"\s*\([^)]*\)", "", h.meaning_lit).strip())
    return [o for o in out if o]


def _present(word: str, text: str) -> bool:
    return bool(re.search(re.escape(word.strip("’'")), text, re.I))


def _plural_variants(phrases: list[str]) -> list[str]:
    out = []
    for p in phrases:
        out.append(p)
        if not p.endswith("s"):
            out.append(p + "s")
            if p.endswith("y"):
                out.append(p[:-1] + "ies")
    return sorted(set(out), key=len, reverse=True)


TERM_SPAN_RE = re.compile(r"`[^`]+` \([^()]*\)")


def _protected(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in TERM_SPAN_RE.finditer(text)]


def _inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def lint(analyses: list[Analysis], translation: str, glossary: dict[str, str] | None = None,
         apply: bool = True, alternatives: dict[str, list[str]] | None = None) -> tuple[str, list[Finding]]:
    """Check ``translation`` against the word analyses; return (possibly amended translation, findings)."""
    text = translation
    findings: list[Finding] = []
    seen: set[str] = set()
    glossary = glossary or {}
    alternatives = alternatives or {}
    glossed: set[str] = set()
    # glossary terms inside compounds (nāmarūpanirodho) also fix the rendering of the term wherever it appears
    source_keys = " ".join(a.key for a in analyses)
    for stem, gloss in glossary.items():
        if gloss and stem[:-1] in source_keys:
            others = [v for v in alternatives.get(stem, []) if v.lower() != gloss.lower() and v.lower() not in gloss.lower()]
            hit = _replace_english(text, _plural_variants(others), gloss, apply, every=True, keep_article=True, plural_aware=True)
            if hit:
                text, phrase = hit
                findings.append(Finding(stem, f"glossary term rendered as '{phrase}'",
                                        f"replaced by '{gloss}'" if apply else f"replace by '{gloss}'", "fix" if apply else "ask"))
    for a in analyses:
        if not a.headwords or a.key in seen:
            continue
        seen.add(a.key)
        h = a.governing(glossary)
        surface = a.surface.strip("’'")
        gstem = _glossary_stem(h, glossary)
        if gstem in glossary and not glossary[gstem]:
            continue                                   # a context-dependent term (dhamma): the translator's rendering stands
        kind = "technical" if gstem in glossary else h.kind
        if kind == "name":
            stem = h.stem.capitalize()
            hit = _replace_english(text, english_variants(h, a.headwords), stem, apply, every=True)
            if hit:
                text, phrase = hit
                findings.append(Finding(surface, f"a name rendered in English as '{phrase}'",
                                        f"replaced by '{stem}'" if apply else f"replace by '{stem}'", "fix" if apply else "ask"))
            elif not _present(h.stem[:6] if len(h.stem) > 6 else h.stem, text):
                findings.append(Finding(surface, f"a name ({h.meaning.split(';')[0]}) does not appear untranslated",
                                        f"put '{stem}' in place of whatever English stands for it"))
        elif kind == "honorific":
            form = honorific_form(h.stem, surface, h.parses, h.family_set)
            hit = _replace_english(text, _plural_variants(english_variants(h, a.headwords)), form, apply, every=True, keep_article=True)
            if hit:
                text, phrase = hit
                findings.append(Finding(surface, f"an honorific rendered in English as '{phrase}'",
                                        f"replaced by '{form}'" if apply else f"replace by '{form}'", "fix" if apply else "ask"))
            elif not (_present(form, text) or _present(h.stem[:5], text)):
                findings.append(Finding(surface, f"an honorific ({h.meaning.split(';')[0]}) does not appear untranslated",
                                        f"put '{form}' in place of whatever English stands for it"))
        elif kind == "technical":
            gloss = glossary.get(gstem) or (h.meaning or h.meaning_2).split(";")[0].strip()
            form = term_form(gstem, surface, h.parses)
            if gstem in glossary:
                # every other rendering of a glossary term (the DPD's "name and form" for nāmarūpa) becomes the gloss
                others = [v for v in _plural_variants(english_variants(h)) if v.lower() != gloss.lower()
                          and not v.lower().startswith(gloss.lower()) and v.lower() not in gloss.lower()]
                hit = _replace_english(text, others, gloss, apply, every=True, keep_article=True, plural_aware=True)
                if hit:
                    text, phrase = hit
                    findings.append(Finding(surface, f"glossary term rendered as '{phrase}'",
                                            f"replaced by '{gloss}'" if apply else f"replace by '{gloss}'", "fix" if apply else "ask"))
            if gstem in glossed:
                continue
            if re.search(r"`" + re.escape(gstem[:-1]) + r"[^`]*`", text, re.I):
                glossed.add(gstem)
                continue
            variants = _plural_variants([gloss] + english_variants(h)) if gstem in glossary else _plural_variants(english_variants(h))
            hit = _replace_english(text, variants, None, apply, gloss_for=form)
            # the word as it stands, or its stem (a model that writes "this Dhamma" or "the cycle of saṃsāra")
            bare = re.compile(r"(?<![`\w])(?:" + re.escape(surface) + "|" + re.escape(gstem) + r")(?![`\w])", re.I)
            if hit:
                text, phrase = hit
                glossed.add(gstem)
                findings.append(Finding(surface, f"technical term rendered as plain '{phrase}'",
                                        f"written as `{form}` ({phrase}) on first use" if apply else f"write `{form}` ({phrase}) on first use", "fix" if apply else "ask"))
            elif next((mm for mm in bare.finditer(text) if not _inside(mm.start(), _protected(text))), None):
                # the Pāḷi word stands untranslated (a title, or a model that kept it): give it the term form
                if apply:
                    m = next(mm for mm in bare.finditer(text) if not _inside(mm.start(), _protected(text)))
                    shown = form if m.group(0).lower() == surface.lower() else gstem
                    text = text[: m.start()] + f"`{shown}` ({gloss})" + text[m.end():]
                glossed.add(gstem)
                findings.append(Finding(surface, "technical term left bare", f"written as `{form}` ({gloss})" if apply else f"write `{form}` ({gloss})",
                                        "fix" if apply else "ask"))
            elif gstem in glossary:
                findings.append(Finding(surface, f"technical term ({gloss}) not shown in the `word` (gloss) form",
                                        f"write it as `{form}` ({gloss}) on its first occurrence, then '{gloss}'"))
        elif a.key in PARTICLES and h.pos == "ind":
            variants = PARTICLE_ENGLISH.get(a.key, []) + english_variants(h)
            if not any((v in text) if not v[0].isalpha() else re.search(r"\b" + re.escape(v) + r"\b", text, re.I) for v in variants):
                findings.append(Finding(surface, f"particle meaning '{h.meaning}' is not rendered",
                                        f"render it (for example '{variants[0] if variants else h.meaning}') where it stands in the sentence"))
        elif (h.pos == "pr" and h.parses and all("pr" in p for p in h.parses) and h.stem not in ("atthi", "hoti")
              and all(x.pos in VERB_POS for x in a.headwords[:3])):   # asati "eats" beside asati "when there is not": skip
            eng = [re.sub(r"\s*\(.*?\)", "", m).strip() for m in (h.meaning or "").split(";") if m.strip()]

            def present_in_text(verb: str) -> bool:      # "comes" matches "come(s)"; "dissolves" matches "dissolve(s)"
                bases = {verb}
                if verb.endswith("ies"):
                    bases.add(verb[:-3] + "y")
                if verb.endswith("es"):
                    bases.add(verb[:-2])
                if verb.endswith("s"):
                    bases.add(verb[:-1])
                return any(re.search(r"\b" + re.escape(b) + r"(?:s|es)?\b", text, re.I) for b in bases)

            if eng and not any(present_in_text(e.split(" ")[0]) for e in eng[:4]):
                hit = _fix_tense(text, eng, apply)
                if hit:
                    text, was, now = hit
                    findings.append(Finding(surface, f"present tense ({h.analysis}) rendered as past '{was}'",
                                            f"changed to '{now}'" if apply else f"change to '{now}'", "fix" if apply else "ask"))
                elif re.search(r"\b(was|were)\s+\w+ing\b|\b\w+ed\b", text, re.I):
                    findings.append(Finding(surface, f"present tense ({h.analysis}) may have been rendered as past",
                                            f"use the present: '{eng[0]}'"))
    text = normalise_terms(text)
    return text, findings


OF_BASE_RE = re.compile(r"\bof (\S+?)(?:,|$)")


def _glossary_stem(h: Headword, glossary: dict[str, str]) -> str:
    """The stem to look a headword up by in the glossary: its own, or the base lemma of an irregular-form entry
    ("masc, nom pl of khandha" for khandhā) when that is the glossary's term."""
    if h.stem in glossary:
        return h.stem
    candidates = []
    m = OF_BASE_RE.search(h.grammar or "")
    if m:
        candidates.append(re.sub(r" \d[\d.]*$", "", m.group(1)))
    candidates.append(re.sub(r"ā$", "a", re.sub(r"ī$", "i", re.sub(r"ū$", "u", h.stem))))     # khandhā: the plural-only entry
    for c in candidates:
        if c in glossary:
            return c
    return h.stem


def _same_stem(a: str, b: str) -> bool:
    a, b = a.lower().strip("*_ "), b.lower().strip("*_ ")
    return a[:6] == b[:6] and a[:1] == b[:1]


def normalise_terms(text: str) -> str:
    """Tidy the `term` (gloss) forms: drop a duplicated "(X)" or "(*X*)" after "`X` (gloss)" (the translate
    model likes to add the Pāḷi in italics), unwrap a term nested inside another's parentheses, and gloss each
    term once — later `word` (gloss) occurrences become the plain gloss."""
    text = re.sub(r"(`([^`]+)` \([^()]*\)) \(\*{0,2}_{0,2}([^()*_]+)_{0,2}\*{0,2}\)",
                  lambda m: m.group(1) if _same_stem(m.group(2), m.group(3)) else m.group(0), text)
    # "dependent origination (*paṭiccasamuppāda*)": English gloss followed by the italic Pāḷi — make it the term form
    text = re.sub(r"\b([A-Za-z][\w -]{2,40}?) \(\*{1,2}([a-zāīūṃṅñṭḍṇḷ]+)\*{1,2}\)", r"`\2` (\1)", text)
    text = re.sub(r"`[^`]+` \((`[^`]+` \([^()]*\))\)", r"\1", text)
    seen: set[str] = set()

    def once(m: re.Match) -> str:
        key = re.sub(r"[ṃoāaṁ]+$", "", m.group(1).lower())
        if key in seen:
            return m.group(2)
        seen.add(key)
        return m.group(0)

    return re.sub(r"`([^`]+)` \(([^()]*)\)", once, text)


def _fix_tense(text: str, meanings: list[str], apply: bool) -> tuple[str, str, str] | None:
    """'was living' -> 'lives' when a DPD meaning shares the participle's first letters; 'were …' -> plural."""
    for m in re.finditer(r"\b(was|were|is|are)\s+(\w+?)ing\b", text, re.I):
        aux, base = m.group(1).lower(), m.group(2).lower()
        for e in meanings:
            verb = e.split(" ")[0]
            if verb[:3] == base[:3]:
                now = verb if aux in ("was", "is") else (verb[:-1] if verb.endswith("s") else verb)
                rest = e[len(verb):]
                if apply:
                    text = text[: m.start()] + now + rest.split(";")[0].rstrip() * 0 + text[m.end():]
                return text, m.group(0), now
    return None


ARTICLE_ONLY_RE = re.compile(r"^((?:the|a|an|this|that|these|those)\s+)", re.I)


def _replace_english(text: str, phrases: list[str], replacement: str | None, apply: bool, every: bool = False,
                     gloss_for: str | None = None, keep_article: bool = False,
                     plural_aware: bool = False) -> tuple[str, str] | None:
    """Find the first of ``phrases`` in ``text`` (with an optional article) and replace it — every occurrence for
    names and honorifics, the first only for a technical term, which becomes `word` (matched phrase). The article
    is dropped before a name ("in Migadāya") and kept before an honorific or a term ("the Bhagavā")."""
    spans = _protected(text)
    for phrase in phrases:
        # "name and form" also matches "name-and-form"
        body = r"[\s-]+".join(re.escape(w) for w in phrase.split())
        pat = re.compile(ARTICLE_RE + r"\b" + body + r"\b", re.I)
        m = next((mm for mm in pat.finditer(text) if not _inside(mm.start(), spans)), None)
        if m:
            if apply:
                def sub(mm: re.Match) -> str:
                    if _inside(mm.start(), spans):
                        return mm.group(0)                    # never edit inside an existing `term` (gloss)
                    article = ARTICLE_ONLY_RE.match(mm.group(0))
                    art = article.group(1) if article else ""
                    core = mm.group(0)[len(art):]
                    if gloss_for is not None:
                        return f"{art}`{gloss_for}` ({core})"
                    rep = replacement
                    if plural_aware and core.lower().endswith("s") and not rep.lower().endswith("s"):
                        rep = rep[:-1] + "ies" if rep.endswith("y") else rep + "s"
                    return (art if keep_article else "") + rep
                if gloss_for is not None:
                    core = m.group(0)[len(ARTICLE_ONLY_RE.match(m.group(0)).group(1)) if ARTICLE_ONLY_RE.match(m.group(0)) else 0:]
                    text = text[: m.start()] + sub(m) + text[m.end():]
                    return text, core
                text = pat.sub(sub, text) if every else text[: m.start()] + sub(m) + text[m.end():]
            return text, phrase
    return None
