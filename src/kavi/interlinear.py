"""Interlinear translation: four lines per sentence.

1. the Pāḷi sentence (numbered as in the source, or by paragraph and sentence);
2. the grammatical analysis, one token per isolated word, in the symbols of the textbook
   (gender, number, ending for a nominal; voice, number, person, tense for a verb) with the dictionary
   lemma in parentheses: ``🚹⨀①(bhagavant) 🟢⨀🤟▶️(viharati)``;
3. the glosses, one per token, separated by bars;
4. the literal translation, rearranged into a normal English sentence.

The Digital Pāḷi Dictionary supplies every candidate parse of every word (sandhi resolved with its own
sandhi entries and the deconstructor); a model chooses among those candidates, glosses each word in the
chosen form and translates the sentence, answering in JSON; a choice outside the candidates falls back to
the first candidate, so the analysis line never says what the dictionary does not. The checker then applies
the house conventions (names, honorifics, technical terms, particles, tense) to the translation line.
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
from .dpd import DPD, Analysis, Headword, VERB_POS, lemma_clean, normalise, parse_words
from .glossary import honorific_form
from .grammar import to_symbol
from .lint import lint
from .segment import Block, parse_markdown, split_sentences

Progress = Callable[[str], None]

NIGGAHITA = str.maketrans({"ṃ": "ṁ"})


def modern(text: str) -> str:
    """The niggahīta written ṁ, the modern spelling the textbook uses (the DPD keeps ṃ)."""
    return text.translate(NIGGAHITA)


# Kaccāyana's sabbanāma (Appendix L of the textbook), which take the pronoun mark whatever the DPD calls them.
SABBANAMA = {"sabba", "katara", "katama", "ubhaya", "itara", "añña", "aññatara", "aññatama", "pubba", "para", "apara",
             "dakkhiṇa", "uttara", "adhara", "ya", "ta", "eta", "ima", "amu", "kiṃ", "eka", "tumha", "amha", "ahaṃ", "tvaṃ"}
VOICE_SYMBOL = {"act": "🟢", "reflx": "🔵", "pass": "🔴", "caus": "🟠"}
GENDERS = ("masc", "fem", "nt", "x")
CASES = ("nom", "acc", "instr", "dat", "abl", "gen", "loc", "voc")
NUMBERS = ("sg", "pl", "dual")
TENSES = ("pr", "aor", "fut", "imp", "opt", "cond", "imperf", "perf")
PERSONS = ("1st", "2nd", "3rd")
NOMINAL_RE = re.compile(r"(?:(masc(?: fem)?(?: & nt)?|masc fem & nt|fem(?: & nt)?|nt|x)\s+)?(nom|acc|instr|dat|abl|gen|loc|voc)\s+(sg|pl|dual)\b")
VERB_RE = re.compile(r"(?:(reflx)\s+)?(pr|aor|fut|imp|opt|cond|imperf|perf)\s+(1st|2nd|3rd)\s+(sg|pl)\b")
PERSON_RE = re.compile(r"\b(1st|2nd|3rd)\s+(nom|acc|instr|dat|abl|gen|loc|voc)\s+(sg|pl)\b")
OF_RE = re.compile(r"\bof (\S+?)(?:,|$)")
ENDINGS = {"a", "ā", "aṃ", "o", "e", "i", "ī", "u", "ū", "ena", "assa", "smiṃ", "mhi", "mhā", "smā", "āya", "āyaṃ", "ehi", "ānaṃ", "esu", "āni", "ehi"}
PUNCT_KEEP = ",;:"
WORD_CHARS = "A-Za-zĀāĪīŪūṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷ’'"
TOKEN_RE = re.compile(rf"[{WORD_CHARS}]+|[{PUNCT_KEEP}]")
ENGLISH_STOP = {"the", "of", "and", "to", "in", "is", "a", "that", "this", "it", "for", "with", "as", "on", "by", "are", "be"}


# --------------------------------------------------------------------------------------
# Parses and their symbols
# --------------------------------------------------------------------------------------


@dataclass
class Parse:
    kind: str                  # noun | verb | pron | ind | prefix | affix | unknown | punct
    lemma: str = ""            # the dictionary form shown in parentheses (ṁ spelling)
    gender: str = ""
    case: str = ""
    number: str = ""
    person: str = ""
    tense: str = ""
    voice: str = ""
    affix: str = ""            # ta, anta, tvā, tuṁ … (participles, absolutives, infinitives)
    members: list[str] = field(default_factory=list)      # compound members, lemma forms
    pos: str = ""
    meaning: str = ""
    headword: Headword | None = None

    def symbols(self) -> str:
        s = to_symbol
        if self.kind == "punct":
            return self.lemma
        if self.kind == "unknown":
            return f"?({self.lemma})"
        if self.kind == "ind":
            return f"⏏️({self.lemma})"
        if self.kind == "prefix":
            return f"🔼({self.lemma})"
        if self.kind == "affix":
            return f"🔽({self.affix})({self.lemma})"
        if self.kind == "verb":
            return (VOICE_SYMBOL.get(self.voice or "act", "🟢") + s.get(self.number, "") + s.get(self.person, "")
                    + s.get(self.tense, "") + f"({self.lemma})")
        core = ""
        if self.kind == "pron":
            core = "*️⃣" + s.get(self.person or "3rd", "")
        gender = "⚧" if (self.kind == "pron" and self.person in ("1st", "2nd")) or self.gender == "x" else s.get(self.gender, "")
        core += gender + s.get(self.number, "") + s.get(self.case, "")
        if self.affix:
            core += f"🔽({self.affix})"
        if self.members:
            return core + "🆎(" + "+".join(self.members) + ")"
        return core + f"({self.lemma})"

    def describe(self) -> str:
        """The parse in words, for the model's candidate list."""
        bits = []
        if self.kind == "pron":
            bits.append("pronoun")
            if self.person:
                bits.append(parse_words(self.person))
        if self.gender and self.gender != "x":
            bits.append(parse_words(self.gender))
        if self.case:
            bits.append(parse_words(self.case))
        if self.number:
            bits.append(parse_words(self.number))
        if self.kind == "verb":
            bits.append(parse_words(self.tense))
            bits.append(parse_words(self.person))
            if self.voice and self.voice != "act":
                bits.append({"reflx": "reflexive", "pass": "passive", "caus": "causative"}[self.voice])
        if self.kind == "affix":
            bits.append("absolutive" if self.affix in ("tvā", "ya", "tvāna") else "infinitive")
        if self.kind == "ind":
            bits.append("indeclinable")
        if self.kind == "prefix":
            bits.append("prefix")
        if self.affix and self.kind == "noun":
            bits.append({"ta": "past participle", "anta": "present participle", "māna": "present participle",
                         "tabba": "potential participle", "anīya": "potential participle"}.get(self.affix, f"affix {self.affix}"))
        if self.members:
            bits.append("compound of " + " + ".join(self.members))
        return ", ".join(b for b in bits if b)

    @property
    def key(self) -> tuple:
        return (self.kind, self.lemma, self.gender, self.case, self.number, self.person, self.tense, self.voice, self.affix)


def _genders(text: str) -> list[str]:
    if "masc fem & nt" in text or text.strip() == "x":
        return ["masc", "fem", "nt"] if "masc fem" in text else ["x"]
    out = []
    for g in ("masc", "fem", "nt"):
        if re.search(rf"\b{g}\b", text):
            out.append(g)
    return out or [""]


def compound_members(h: Headword) -> list[str]:
    """The members of a compound headword in lemma form: the DPD's morphological construction when it is two or
    more plain words, else its compound construction (inflected members stripped of their endings)."""
    if not h.compound_type and "comp" not in (h.grammar or ""):
        return []
    # the morphological construction first: "avijjā + paccaya + ā", "anuloma + paṭiloma + aṃ" — lemma members, then the ending
    for alt in (h.construction or "").split("|"):
        parts = [p.strip() for p in alt.split(" + ")]
        while len(parts) > 2 and (len(parts[-1]) <= 2 or parts[-1] in ENDINGS):
            parts.pop()
        if len(parts) >= 2 and all(re.fullmatch(r"[a-zāīūṃṅñṭḍṇḷ]+", p) for p in parts):
            return [modern(p) for p in parts]
    cc = h.compound_construction or ""
    if not cc:
        return []
    cc = re.sub(r"<b>[^<]*</b>", "", cc)
    parts = [p.strip() for p in (re.split(r"\s+ca(?:\s+|$)", cc) if "dvanda" in h.compound_type else cc.split(" + "))]
    parts = [modern(p) for p in parts if p]
    return parts if len(parts) >= 2 else []


def _affix(h: Headword, surface: str) -> str:
    if h.pos == "abs":
        return "ya" if surface.endswith("ya") and not surface.endswith("tvā") else ("tvāna" if surface.endswith("tvāna") else "tvā")
    if h.pos == "inf":
        return "tuṁ"
    if h.pos in ("pp", "prp", "ptp"):
        parts = [re.sub(r"[^a-zāīūṃṅñṭḍṇḷ]", "", x) for x in (h.construction or "").split("|")[0].split("+")]
        if h.pos == "prp":
            return "māna" if "māna" in parts else "anta"
        if h.pos == "ptp":
            return next((modern(x) for x in reversed(parts) if x in ("tabba", "anīya", "ṇīya", "ya", "teyya")), "tabba")
        return next((modern(x) for x in reversed(parts) if x in ("ta", "ita", "na", "ina", "ṇa", "tta")), "ta")
    return ""


def candidates(h: Headword, surface: str) -> list[Parse]:
    """Every parse the DPD allows for this headword as the form ``surface``."""
    g = h.grammar or h.pos
    base = OF_RE.search(g)
    # the base word for an inflected-form headword (bhagavā "nom sg of bhagavant", me "1st acc sg of ahaṃ"), an
    # aorist, absolutive or infinitive ("aor of manasikaroti"); a participle keeps its own lemma (jhāyanta)
    use_base = base is not None and (h.pos in VERB_POS or h.pos in ("abs", "inf") or NOMINAL_RE.search(g) or PERSON_RE.search(g))
    lemma = modern(base.group(1) if use_base else h.stem)
    meaning = "; ".join(m.strip() for m in (h.meaning or h.meaning_2 or "").split(";")[:3])
    members = [] if h.kind == "name" else compound_members(h)          # a place name is not shown as a compound
    common = dict(pos=h.pos, meaning=meaning, headword=h, members=members)
    if h.pos == "sandhi":
        return []
    if h.pos in ("abs", "inf"):
        return [Parse("affix", lemma, affix=_affix(h, surface), **common)]
    if h.pos == "prefix":
        return [Parse("prefix", lemma, **common)]
    if h.pos in ("ind", "idiom", "suffix", "letter", "cs", "ve", "abbrev"):
        abbrev = re.search(r"abbrev of (\S+)", g)                       # ti for iti, va for iva or eva
        out = [Parse("ind", modern(abbrev.group(1) if abbrev else h.stem), **common)]
        m = NOMINAL_RE.search(g)
        if h.pos == "ind" and "adv" in g and base is not None and m:   # sattāhaṃ "adv, acc sg of sattāha": the noun too
            gender = m.group(1) or ("fem" if lemma.endswith(("ā", "i", "ī")) else "masc")
            out.append(Parse("noun", lemma, gender=gender.split()[0], case=m.group(2), number=m.group(3), **common))
        return out
    out: list[Parse] = []
    if h.pos in VERB_POS or h.pos == "verb":
        voice = "caus" if re.search(r"\bcaus\b", g) else "pass" if re.search(r"\bpass\b", g) else ""
        sources = h.parses or [g]
        for p in sources:
            m = VERB_RE.search(p)
            if m:
                out.append(Parse("verb", lemma, number=m.group(4), person=m.group(3), tense=m.group(2),
                                 voice="reflx" if m.group(1) else voice, **common))
        return _dedupe(out)
    pron = h.pos == "pron" or h.stem in SABBANAMA or lemma in SABBANAMA
    affix = _affix(h, surface)
    sources = h.parses or [g]
    for p in sources:
        m = PERSON_RE.search(p)
        if m and pron:
            out.append(Parse("pron", lemma, person=m.group(1), case=m.group(2), number=m.group(3), **common))
            continue
        m = NOMINAL_RE.search(p)
        if not m:
            continue
        genders = _genders(m.group(1) or "")
        if genders == [""] and h.pos in ("masc", "fem", "nt"):
            genders = [h.pos]
        for gender in genders:
            if pron:
                person = "3rd"
                if lemma in ("ahaṁ", "amha"):
                    person = "1st"
                elif lemma in ("tvaṁ", "tumha"):
                    person = "2nd"
                out.append(Parse("pron", lemma, gender=gender, case=m.group(2), number=m.group(3), person=person, **common))
            else:
                out.append(Parse("noun", lemma, gender=gender, case=m.group(2), number=m.group(3), affix=affix, **common))
    return _dedupe(out)


def _dedupe(parses: list[Parse]) -> list[Parse]:
    seen: set[tuple] = set()
    out = []
    for p in parses:
        if p.key not in seen:
            seen.add(p.key)
            out.append(p)
    return out


# --------------------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------------------


@dataclass
class Token:
    surface: str                       # as it stands in the text (or the sandhi part)
    key: str                           # lookup key (ṃ spelling)
    analysis: Analysis | None = None
    candidates: list[Parse] = field(default_factory=list)
    chosen: Parse | None = None
    gloss: str = ""
    punct: bool = False

    @property
    def parse(self) -> Parse:
        if self.chosen:
            return self.chosen
        if self.candidates:
            return self.candidates[0]
        if self.punct:
            return Parse("punct", self.surface)
        return Parse("unknown", modern(self.surface))


def tokenise(text: str) -> list[tuple[str, str, bool]]:
    """(surface, lookup key, is_punct) for the words and kept punctuation of a sentence. Quotation marks are
    dropped; a word ending in ``n`` before the closing ``ti`` of a quotation gets its niggahīta back."""
    raw = [(m.group(0), m.start()) for m in TOKEN_RE.finditer(text)]
    out: list[tuple[str, str, bool]] = []
    for i, (tok, pos) in enumerate(raw):
        if tok in PUNCT_KEEP:
            if out and not out[-1][2] and i + 1 < len(raw) and raw[i + 1][0] not in PUNCT_KEEP:
                out.append((tok, tok, True))
            continue
        word = tok.strip("’'")
        if not word or not re.search(r"[a-zāīūṃṅñṭḍṇḷ]", word.lower()):
            continue
        key = normalise(word)
        nxt = raw[i + 1][0] if i + 1 < len(raw) else ""
        between = text[pos + len(tok): raw[i + 1][1]] if i + 1 < len(raw) else ""
        if nxt.lower() in ("ti", "’ti") and key.endswith("n") and ("”" in between or "'" in between or '"' in between or "’" in between):
            key = key[:-1] + "ṃ"
        out.append((word, key, False))
    while out and out[-1][2]:
        out.pop()
    return out


def _sandhi_parts(h: Headword) -> list[str]:
    """``imassa + uppādā`` from a DPD sandhi headword's construction; ``tu > tv + eva`` gives tu, eva."""
    first = (h.construction or "").split("|")[0]
    parts = []
    for p in first.split(" + "):
        p = p.split(">")[0].strip()
        p = re.sub(r"[^a-zāīūṃṅñṭḍṇḷ]", "", p)
        if p:
            parts.append(p)
    return parts if len(parts) >= 2 else []


def analyse_tokens(dpd: DPD, text: str) -> list[Token]:
    tokens: list[Token] = []
    for surface, key, punct in tokenise(text):
        if punct:
            tokens.append(Token(surface, key, punct=True))
            continue
        a = dpd.analyse(key)
        if a.headwords and a.headwords[0].pos == "sandhi":
            parts = _sandhi_parts(a.headwords[0])
            if parts:
                for p in parts:
                    sub = dpd.analyse(p)
                    tokens.append(Token(p, normalise(p), sub, _candidates_of(sub, p)))
                continue
        if a.headwords:
            cands = _candidates_of(a, surface)
            _fill_members(dpd, a, cands)
            split = a.best_split
            if not cands and split is not None and len(split.parts) >= 2 and all(x.headwords for x in split.analyses):
                for part in split.analyses:                      # sūriyova: no reading of the whole, a split of two words
                    tokens.append(Token(part.key, part.key, part, _candidates_of(part, part.key)))
                continue
            tokens.append(Token(surface, key, a, cands))
            continue
        split = a.best_split
        if split is not None and split.source.startswith("lengthened") and len(split.parts) == 1:
            sub = dpd.analyse(split.parts[0])
            tokens.append(Token(surface, split.parts[0], sub, _candidates_of(sub, surface)))
            continue
        if split is not None and split.analyses and any(x.headwords for x in split.analyses):
            for part in split.analyses:
                tokens.append(Token(part.key, part.key, part, _candidates_of(part, part.key)))
            continue
        tokens.append(Token(surface, key, a))
    return tokens


def _fill_members(dpd: DPD, a: Analysis, cands: list[Parse]) -> None:
    """A compound's members in lemma form for the noun readings that lack them (an adverb entry's noun reading,
    avijjāpaccayā), from the DPD deconstructor's split of the form."""
    todo = [p for p in cands if p.kind == "noun" and not p.members and p.headword is not None and "comp" in (p.headword.grammar or "")]
    if not todo:
        return
    splits = [s.parts for s in a.splits if len(s.parts) >= 2] or [[normalise(x) for x in sp.split(" + ")] for sp in dpd.deconstruct(a.key) if " + " in sp]
    for parts in splits[:1]:
        analyses = [dpd.analyse(x, 1) for x in parts]
        if not all(x.headwords for x in analyses):
            continue
        members = []
        for x in analyses:
            h = next((hw for hw in x.headwords if hw.pos not in ("ind", "sandhi", "ve", "cs", "letter")), x.headwords[0])
            base = OF_RE.search(h.grammar or "")
            members.append(modern(base.group(1) if base and h.pos == "ind" else h.stem))
        for p in todo:
            p.members = members


def _candidates_of(a: Analysis, surface: str, max_headwords: int = 6) -> list[Parse]:
    out: list[Parse] = []
    # a noun or verb reading before an adverb headword made of the same form (sattāhaṁ: the noun before the adverb);
    # the grammarians' terms (ti the verbal ending, a letter, a suffix) last
    def rank(h: Headword) -> int:
        g = h.grammar or ""
        if h.pos in ("ve", "cs", "letter", "suffix", "root", "abbrev") or "prefix" in g or ("in comps" in g and h.pos != "ind"):
            return 2                                    # the grammarians' terms, prefixes and compound-only stems last
        adverb_of_noun = h.pos == "ind" and re.search(r"\badv\b.*\bof\b", g)
        return 1 if adverb_of_noun and any(x.pos not in ("ind", "sandhi") for x in a.headwords[:4]) else 0
    ordered = sorted(a.headwords, key=rank)
    for h in ordered[:max_headwords]:
        out.extend(candidates(h, surface))
    out = _dedupe(out)
    # a noun reading before the adverb made of the same form, so the fallback is the inflected word
    out.sort(key=lambda p: 1 if (p.kind == "ind" and any(q.kind != "ind" and q.lemma != p.lemma for q in out) and p.headword is not None and "adv" in (p.headword.grammar or "")) else 0)
    return out[:10]


# --------------------------------------------------------------------------------------
# The model's choice
# --------------------------------------------------------------------------------------

SYSTEM = (
    "You are a Pāli grammarian and a literal translator. For every word of a Pāli sentence you choose the one "
    "dictionary parse (Digital Pāḷi Dictionary) that the sentence requires, you gloss the word in that form, and you "
    "translate the sentence literally into normal English. You answer with JSON only."
)


def prompt_for(unit_text: str, tokens: list[Token], glossary: dict[str, str], context: list[tuple[str, str]]) -> str:
    lines = [f"Sentence: {unit_text}"]
    if context:
        lines.append("\nPreceding sentences and their translations (keep their renderings for the words and formulas they share with this sentence):")
        lines.extend(f"- {s}\n  → {t}" for s, t in context)
    lines.append("\nWords, with the candidate parses the dictionary allows (a word written together with another in the sentence is listed as its parts):")
    for n, t in enumerate(tokens, 1):
        if t.punct:
            continue
        lines.append(f"{n}. {modern(t.surface)}")
        if not t.candidates:
            lines.append("   (not in the dictionary: gloss it as best you can)")
        for c, p in enumerate(t.candidates, 1):
            lines.append(f"   {c}. {p.lemma} ({p.describe()}) — {p.meaning or '—'}")
    terms = {modern(k): v for k, v in glossary.items()}
    used = [f"{k} = {v}" for k, v in terms.items() if any(k[:-1] in (t.key or "") for t in tokens if not t.punct)]
    rules = [
        "For every word choose the candidate whose grammatical form the sentence requires: an adjective or participle agrees with its noun in gender, number and case; the verb's person and number are its subject's; a locative absolute takes the locative participle.",
        "The gloss renders only that word in that form, in one to four English words, with the preposition the case needs where English needs one (\"by me\", \"in the night\", \"of the week\"), and no explanation.",
        "Names stay in their Pāli stem form; honorifics and titles stay as they stand in the text (Bhagavā, bhikkhave, bhante).",
        "The translation renders every word of the sentence, keeps a present-tense verb in the present, is rearranged into a normal English sentence, and adds nothing that the Pāli does not say.",
    ]
    if used:
        rules.append("These technical terms take these glosses: " + "; ".join(used) + ".")
    lines.append("\nRules:")
    lines.extend(f"{i}. {r}" for i, r in enumerate(rules, 1))
    lines.append('\nAnswer with JSON only, one entry per numbered word above, repeating the word, in this form: '
                 '{"words": [{"n": 1, "word": "evaṁ", "parse": 1, "gloss": "thus"}, {"n": 2, "word": "me", "parse": 3, "gloss": "by me"}], "translation": "…"}')
    return "\n".join(lines)


def parse_answer(text: str, tokens: list[Token]) -> tuple[dict[int, int], dict[int, str], str]:
    """(chosen parse index per word number, gloss per word number, translation)."""
    start = text.find("{")
    end = text.rfind("}")
    data: dict = {}
    if start != -1 and end > start:
        for cand in (text[start: end + 1], re.sub(r",\s*([}\]])", r"\1", text[start: end + 1])):
            try:
                data = json.loads(cand)
                break
            except json.JSONDecodeError:
                continue
    choice: dict[int, int] = {}
    gloss: dict[int, str] = {}
    surfaces = [normalise(getattr(t, "surface", "") or "") for t in tokens]
    cursor = 0
    for w in data.get("words", []) if isinstance(data, dict) else []:
        if not isinstance(w, dict):
            continue
        n = None
        echoed = normalise(str(w.get("word", "")))
        if echoed:                                                   # align by the echoed word, in order
            for i in range(cursor, len(surfaces)):
                if surfaces[i] and (surfaces[i] == echoed or echoed.startswith(surfaces[i]) or surfaces[i].startswith(echoed)):
                    n = i + 1
                    break
        if n is None:
            try:
                n = int(w.get("n"))
            except (TypeError, ValueError):
                continue
        if 1 <= n <= len(tokens):
            cursor = n
            try:
                choice[n] = int(w.get("parse"))
            except (TypeError, ValueError):
                pass
            g = w.get("gloss")
            if isinstance(g, str) and g.strip():
                gloss[n] = g.strip()
    translation = data.get("translation", "") if isinstance(data, dict) else ""
    if not translation:
        for m in re.finditer(r'"translation"\s*:\s*"((?:[^"\\]|\\.)*)"', text):
            translation = m.group(1).encode().decode("unicode_escape") if "\\u" in m.group(1) else m.group(1).replace('\\"', '"')
    return choice, gloss, (translation or "").strip()


# --------------------------------------------------------------------------------------
# Units and the document
# --------------------------------------------------------------------------------------


@dataclass
class Unit:
    number: str
    text: str                                  # the Pāḷi sentence or verse line
    verse: bool = False
    tokens: list[Token] = field(default_factory=list)
    translation: str = ""
    from_cache: bool = False
    raw: str = ""

    @property
    def analyses(self) -> list[Analysis]:
        return [t.analysis for t in self.tokens if t.analysis is not None]

    def analysis_line(self) -> str:
        return " ".join(t.parse.symbols() for t in self.tokens)

    def gloss_line(self) -> str:
        return " | ".join(t.gloss or t.surface for t in self.tokens)


def load_segments(path: Path) -> list[tuple[str, str]]:
    """(number, text) from SuttaCentral's segment JSON (the API's ``root_text`` map or a bilara root file)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "root_text" in data:
        data = data["root_text"]
    out = []
    for k, v in data.items():
        num = k.split(":")[-1]
        if not re.match(r"\d", num) or num.startswith("0."):
            continue
        out.append((num, v.strip()))
    return out


def _norm(s: str) -> str:
    return re.sub(r"[\s“”\"‘’'—–-]+", "", modern(s)).lower()


def match_segments(paragraph: str, segments: list[tuple[str, str]], start: int) -> tuple[list[tuple[str, str]], int] | None:
    """Consecutive segments from ``start`` whose texts make up the paragraph; (units, next start) or None."""
    target = _norm(paragraph)
    i, pos, out = start, 0, []
    while pos < len(target) and i < len(segments):
        num, text = segments[i]
        n = _norm(text)
        if not n:
            i += 1
            continue
        if target.startswith(n, pos):
            out.append((num, text))
            pos += len(n)
            i += 1
        elif not out:
            i += 1                      # skip segments before the paragraph (headings, numbers)
        else:
            return None
    return (out, i) if out and pos == len(target) else None


CASE_OF_PREPOSITION = {"by": "instr", "with": "instr", "through": "instr", "to": "dat", "for": "dat", "from": "abl",
                       "of": "gen", "in": "loc", "at": "loc", "on": "loc", "among": "loc", "into": "acc"}


def reconcile_case(chosen: Parse | None, candidates: list[Parse], gloss: str) -> Parse | None:
    """The model's gloss says "by me" but its parse says dative: take the candidate of the same lemma whose case the
    gloss's preposition names, when there is exactly such a candidate."""
    if chosen is None or chosen.kind not in ("noun", "pron") or not gloss:
        return chosen
    m = re.match(r"^(by|with|through|to|for|from|of|in|at|on|among|into)\b", gloss.strip(), re.I)
    if not m:
        return chosen
    wanted = CASE_OF_PREPOSITION[m.group(1).lower()]
    if chosen.case == wanted or (wanted == "instr" and chosen.case == "instr"):
        return chosen
    same = [p for p in candidates if p.kind == chosen.kind and p.lemma == chosen.lemma and p.case == wanted
            and (p.number == chosen.number) and (not chosen.gender or not p.gender or p.gender == chosen.gender)]
    return same[0] if len(same) >= 1 else chosen


PREFIX_RE = re.compile(r"^(?:(?:by|to|for|from|of|in|at|on|with|the|a|an|this|that|these|those|his|her|its|their)\s+)+", re.I)


def _conventional(gloss: str, form: str) -> str:
    """A gloss in the house convention: the name, honorific or glossary gloss ``form``, keeping whatever preposition
    and article the model's gloss opened with ("to the brahmin" -> "to the brāhmaṇa")."""
    if form.lower() in gloss.lower():
        return gloss
    m = PREFIX_RE.match(gloss)
    return (m.group(0) if m else "") + form


def is_pali(dpd: DPD, text: str) -> bool:
    words = [w for w, _, p in tokenise(text) if not p]
    if not words:
        return False
    english = sum(1 for w in words if w.lower() in ENGLISH_STOP)
    known = sum(1 for w in words if dpd.known(normalise(w)))
    return english / len(words) < 0.2 and known / len(words) >= 0.6


class Interlinear:
    def __init__(self, settings: Settings, dpd: DPD, models, model_role: str = "review", progress: Progress | None = None,
                 use_cache: bool = True):
        self.s = settings
        self.dpd = dpd
        self.models = models
        self.role = model_role
        self.progress = progress or (lambda msg: sys.stderr.write(msg + "\n"))
        self.calls = 0
        self._glossed: set[str] = set()
        self.cache_path = settings.cache_dir / "interlinear.json" if use_cache else None
        self.cache: dict[str, dict] = {}
        if self.cache_path and self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.cache = {}

    # -- cache --------------------------------------------------------------------------

    def _key(self, text: str) -> str:
        model = self.s.eval_model if self.role == "review" else self.s.translate_model
        raw = "\x00".join([modern(text).strip(), Path(model).name, "|".join(self.s.glossary_terms), "interlinear-2"])
        return hashlib.sha256(raw.encode()).hexdigest()

    def save_cache(self) -> None:
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    # -- one unit ---------------------------------------------------------------------------

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
            for stem, alts in alternatives.items():               # name-and-form -> phenomenal objects, inside compounds too
                if stem[:-1] in (t.key or "") and t.gloss:
                    for alt in sorted(alts, key=len, reverse=True):
                        t.gloss = re.sub(r"\b" + re.escape(alt) + r"s?\b", glossary[stem], t.gloss, flags=re.I)
            h = t.chosen.headword if t.chosen else None
            if h is not None:
                if h.stem in glossary:
                    t.gloss = _conventional(t.gloss, glossary[h.stem])
                elif h.kind == "name":
                    t.gloss = _conventional(t.gloss, modern(h.stem).capitalize())
                elif h.kind == "honorific":
                    t.gloss = _conventional(t.gloss, modern(honorific_form(h.stem, t.surface, h.parses, h.family_set)))
                if not t.gloss:
                    t.gloss = "(end quote)" if t.chosen and t.chosen.lemma == "iti" else re.sub(r"\s*'\s*'\s*$", "", (h.meaning or h.meaning_2 or "?").split(";")[0]).strip()
            elif not t.gloss:
                t.gloss = "?"
        if not translation:
            translation = " ".join(t.gloss for t in unit.tokens if not t.punct)
        fixed, _ = lint(unit.analyses, translation, glossary, alternatives=self.s.glossary_alternatives)
        fixed = self._gloss_once(fixed)
        unit.translation = modern(fixed) if re.search(r"[ṃ]", fixed) else fixed

    def _gloss_once(self, text: str) -> str:
        """A technical term is written `word` (gloss) on its first use in the document and as the plain gloss after."""
        def once(m: re.Match) -> str:
            key = re.sub(r"[ṃṁoāaeīiū]+$", "", m.group(1).lower())
            if key in self._glossed:
                return m.group(2)
            self._glossed.add(key)
            return m.group(0)
        return re.sub(r"`([^`]+)` \(([^()]*)\)", once, text)

    def process(self, unit: Unit, context: list[tuple[str, str]]) -> None:
        unit.tokens = analyse_tokens(self.dpd, unit.text)
        key = self._key(unit.text)
        if key in self.cache:
            c = self.cache[key]
            unit.from_cache = True
            self._apply(unit, {int(k): v for k, v in c.get("choice", {}).items()}, {int(k): v for k, v in c.get("gloss", {}).items()}, c.get("translation", ""))
            return
        model = self.models.get(self.role)
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt_for(modern(unit.text), unit.tokens, self.s.glossary_map, context)}]
        choice: dict[int, int] = {}
        gloss: dict[int, str] = {}
        translation = ""
        for temp in (self.s.temperature, 0.3):
            self.calls += 1
            reply = model.chat(messages, max_tokens=self.s.max_tokens, temperature=temp, thinking=self.s.thinking)
            unit.raw = reply.text
            choice, gloss, translation = parse_answer(reply.text, unit.tokens)
            if gloss or translation:
                break
        self._apply(unit, choice, gloss, translation)
        self.cache[key] = {"choice": {str(k): v for k, v in choice.items()}, "gloss": {str(k): v for k, v in gloss.items()},
                           "translation": translation, "source": unit.text}

    # -- the document -----------------------------------------------------------------------

    def units_of(self, text: str, segments: list[tuple[str, str]] | None, para_no: int, seg_pos: int) -> tuple[list[Unit], int, bool]:
        """The units of one paragraph; (units, next segment position, verse?)."""
        lines = [ln for ln in text.split("\n") if ln.strip()]
        verse = len(lines) > 1 and all(len(ln.split()) <= 12 for ln in lines)
        pieces: list[tuple[str, str]] = []
        if segments:
            m = match_segments(text, segments, seg_pos)
            if m:
                pieces, seg_pos = m
        if not pieces:
            if verse:
                pieces = [(f"{para_no}.{i}", ln.strip()) for i, ln in enumerate(lines, 1)]
            else:
                pieces = [(f"{para_no}.{i}", s) for i, s in enumerate(split_sentences(" ".join(lines)), 1)]
        return [Unit(num, txt, verse=verse) for num, txt in pieces], seg_pos, verse

    def render_group(self, u: Unit, with_translation: bool = True) -> list[str]:
        lines = [f"{u.number} {modern(u.text).strip()}  ", u.analysis_line() + "  ", u.gloss_line() + ("  " if with_translation else "")]
        if with_translation:
            lines.append(u.translation)
        return lines

    def translate_markdown(self, text: str, segments: list[tuple[str, str]] | None = None) -> "InterlinearResult":
        t0 = time.time()
        blocks = parse_markdown(text)
        units_all: list[Unit] = []
        seg_pos = 0
        para_no = 0
        recent: list[tuple[str, str]] = []
        for b in blocks:
            if b.kind != "para" or not b.translatable or not is_pali(self.dpd, b.text):
                continue
            para_no += 1
            units, seg_pos, verse = self.units_of(b.text, segments, para_no, seg_pos)
            out: list[str] = []
            for i, u in enumerate(units):
                self.progress(f"[{u.number}] {u.text[:60]}{'…' if len(u.text) > 60 else ''}")
                self.process(u, recent[-self.s.context_segments:])
                recent.append((modern(u.text), u.translation))
                units_all.append(u)
                if out:
                    out.append("")
                out.extend(self.render_group(u, with_translation=not verse))
            if verse and units:
                out.append("")
                out.extend(f"{u.translation}  " for u in units[:-1])
                out.append(units[-1].translation)
            b.kind = "verbatim"
            b.lines = out
        self.save_cache()
        from .segment import render
        return InterlinearResult(render(blocks), units_all, time.time() - t0, self.calls)


@dataclass
class InterlinearResult:
    markdown: str
    units: list[Unit]
    seconds: float
    model_calls: int

    def report(self) -> str:
        lines = []
        for u in self.units:
            lines.append(f"### {u.number}\n\n{u.text}\n")
            if u.from_cache:
                lines.append("_(from cache)_\n")
            for n, t in enumerate(u.tokens, 1):
                if t.punct:
                    continue
                chosen = t.parse
                alts = [p for p in t.candidates if p is not chosen]
                lines.append(f"- {n}. {t.surface} → {chosen.symbols()} “{t.gloss}”" + (f" (other parses: {len(alts)})" if alts else ""))
            if u.raw and not u.from_cache:
                lines.append(f"\n<details><summary>model answer</summary>\n\n```\n{u.raw[:1500]}\n```\n</details>")
            lines.append("")
        return "\n".join(lines)
