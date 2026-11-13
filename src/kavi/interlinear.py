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

This module holds the tokens, the candidate parses, the prompt and the answer's parser; the document is
driven by ``pipeline.Translator``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .dpd import DPD, Analysis, Headword, VERB_POS, normalise, parse_words
from .grammar import to_symbol
from .language import LANGUAGE, PRONOUNS
from .lint import _clean_dict_gloss
from .segment import PH_RE, split_sentences

NIGGAHITA = str.maketrans({"ṃ": "ṁ"})


def modern(text: str) -> str:
    """The niggahīta written ṁ, the modern spelling the textbook uses (the DPD keeps ṃ); Sanskrit keeps ṃ."""
    return text.translate(NIGGAHITA) if LANGUAGE["niggahita"] else text


VOICE_SYMBOL = {"act": "🟢", "reflx": "🔵", "pass": "🔴", "caus": "🟠"}
TADDHITA = {"tva", "tā", "ka", "ika", "in", "vat", "mat", "maya", "tara", "tama", "ya"}
GENDERS = ("masc", "fem", "nt", "x")
CASES = ("nom", "acc", "instr", "dat", "abl", "gen", "loc", "voc")
NUMBERS = ("sg", "pl", "dual")
TENSES = ("pr", "aor", "fut", "imp", "opt", "cond", "imperf", "perf", "pfut", "bened")
PERSONS = ("1st", "2nd", "3rd")
NOMINAL_RE = re.compile(r"(?:(masc(?: fem)?(?: & nt)?|masc fem & nt|fem(?: & nt)?|nt|x)\s+)?(nom|acc|instr|dat|abl|gen|loc|voc)\s+(sg|pl|dual)\b")
VERB_RE = re.compile(r"(?:(reflx)\s+)?(pr|aor|fut|imp|opt|cond|imperf|perf|pfut|bened)\s+(1st|2nd|3rd)\s+(sg|pl|dual)\b")
PERSON_RE = re.compile(r"\b(1st|2nd|3rd)\s+(nom|acc|instr|dat|abl|gen|loc|voc)\s+(sg|pl|dual)\b")
OF_RE = re.compile(r"\bof (\S+?)(?:[,;]|$)")                        # "abs of upasaṃkrāmati; BHS § 2.64 …": the lemma stops at the note
ENDINGS = {"a", "ā", "aṃ", "o", "e", "i", "ī", "u", "ū", "ena", "assa", "smiṃ", "mhi", "mhā", "smā", "āya", "āyaṃ", "ehi", "ānaṃ", "esu", "āni", "ehi"}
PUNCT_KEEP = ",;:"
WORD_CHARS = "A-Za-zĀāĪīŪūṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷṚṛṜṝḸḹŚśṢṣḤḥ’‘'"
TOKEN_RE = re.compile(rf"[{WORD_CHARS}]+|[{PUNCT_KEEP}]")
TOKEN_RE_SA = re.compile(rf"[{WORD_CHARS}]+(?:-[{WORD_CHARS}]+)+|[{WORD_CHARS}]+|[{PUNCT_KEEP}]")   # vedanā-saṃjñā-…: one compound
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
            if LANGUAGE["code"] == "sa" and self.members:              # tadyathā: ⏏️🆎(tad+yathā), the author's form
                return "⏏️🆎(" + "+".join(self.members) + ")"
            return f"⏏️({self.lemma})"
        if self.kind == "prefix":
            return f"🔼({self.lemma})"
        if self.kind == "affix":
            if LANGUAGE["code"] == "sa" and self.members:              # triḥpradakṣiṇīkṛtvā: 🔽(tvā)🆎(tri+pradakṣiṇa+karoti)
                return f"🔽({self.affix})🆎(" + "+".join(self.members) + ")"
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
        while len(parts) > 2 and (len(parts[-1]) <= 2 or parts[-1] in ENDINGS or parts[-1] in TADDHITA
                                  or (h.pos in ("pp", "prp", "ptp") and parts[-1] in ("ta", "māna", "anta", "at", "tavya", "anīya", "ya", "tavat"))):
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
        return "tum" if LANGUAGE["code"] == "sa" else "tuṁ"
    if h.pos in ("pp", "prp", "ptp"):
        parts = [re.sub(r"[^a-zāīūṃṅñṭḍṇḷṛśṣ]", "", x) for x in (h.construction or "").split("|")[0].split("+")]
        if h.pos == "prp":
            return "māna" if "māna" in parts else ("at" if "at" in parts else "anta")
        if h.pos == "ptp":
            return next((modern(x) for x in reversed(parts) if x in ("tabba", "anīya", "ṇīya", "ya", "teyya", "tavya")), "tavya" if LANGUAGE["code"] == "sa" else "tabba")
        return next((modern(x) for x in reversed(parts) if x in ("ta", "ita", "na", "ina", "ṇa", "tta", "tavat")), "ta")
    if h.pos in ("masc", "fem", "nt", "adj") and h.construction and " + " in h.construction:
        last = h.construction.split("|")[0].split(" + ")[-1].strip()
        if last in TADDHITA:
            return last
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
    pron = h.pos == "pron" or h.stem in PRONOUNS or lemma in PRONOUNS
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
                if lemma in ("ahaṁ", "amha", "aham", "asmad"):
                    person = "1st"
                elif lemma in ("tvaṁ", "tumha", "tvam", "yuṣmad"):
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
    src: str = ""                      # the word of the text a sandhi or compound split part was cut from

    @property
    def parse(self) -> Parse:
        if self.chosen:
            return self.chosen
        if self.candidates:
            return self.candidates[0]
        if self.punct:
            return Parse("punct", self.surface)
        return Parse("unknown", modern(self.surface))

    @property
    def first(self) -> Parse | None:
        """The lexicon's first reading of the word, or nothing (punctuation, an unknown word)."""
        return self.candidates[0] if self.candidates else None

    @property
    def only_names(self) -> bool:
        """Every reading the dictionary offers for this word is a name."""
        return bool(self.candidates) and all(c.headword is not None and c.headword.kind == "name" for c in self.candidates)


PRIVATIVE_PREFIXES = ("niṣ", "niś", "nis", "nir", "niḥ")       # nis- as the sandhi writes it before a consonant


def privative_rest(stem: str) -> str:
    """niṣprapañca -> prapañca, nirvikalpa -> vikalpa: the word a Sanskrit compound with the privative nis- ends in, which
    the dictionaries list as one headword and so give no members; a glossary term inside it keeps its rendering."""
    for p in PRIVATIVE_PREFIXES:
        if stem.startswith(p) and len(stem) - len(p) >= 4:
            return stem[len(p):]
    return ""


def token_terms(t: "Token") -> set[str]:
    """The stems a token stands for: its headword and that headword's compound members (ṃ spelling), so that a
    glossary term is matched as a word or a member, never as a substring (bhava is not in bhavati)."""
    heads = []
    if t.chosen and t.chosen.headword:
        heads.append(t.chosen.headword)
    if t.analysis and t.analysis.headwords:
        heads.append(t.analysis.headwords[0])
    out: set[str] = set(t.chosen.members if t.chosen else [])
    if t.analysis and t.analysis.headwords and t.analysis.headwords[0].pos == "ind":
        out.update(h.stem for h in t.analysis.headwords[:3])      # dukkhaṃ: the adverb's entry first, the noun dukkha behind it
    for h in heads:
        out.add(h.stem)
        if h.pos in VERB_POS:                            # bhavati is "bhava + ti": a verbal stem, not the noun bhava
            continue
        if LANGUAGE["code"] == "sa" and (rest := privative_rest(h.stem)):
            out.add(rest)
        for cons in (h.compound_construction, h.construction):
            for alt in re.sub(r"</?b>", "", cons or "").split("|"):
                out.update(m.strip() for m in alt.split(" + ") if m.strip())
    return {x.replace("ṁ", "ṃ") for x in out}


def terms_of(tokens) -> set[str]:
    """The stems the words of a sentence stand for."""
    return set().union(*(token_terms(t) for t in tokens if not t.punct))


def tokenise(text: str) -> list[tuple[str, str, bool]]:
    """(surface, lookup key, is_punct) for the words and kept punctuation of a sentence. Quotation marks are
    dropped; a word ending in ``n`` before the closing ``ti`` of a quotation gets its niggahīta back."""
    rx = TOKEN_RE_SA if LANGUAGE["code"] == "sa" else TOKEN_RE
    raw = [(m.group(0), m.start()) for m in rx.finditer(text)]
    out: list[tuple[str, str, bool]] = []
    for i, (tok, pos) in enumerate(raw):
        if tok in PUNCT_KEEP:
            if out and not out[-1][2] and i + 1 < len(raw) and raw[i + 1][0] not in PUNCT_KEEP:
                out.append((tok, tok, True))
            continue
        word = tok.strip("’‘'")
        if not word or not re.search(r"[a-zāīūṃṅñṭḍṇḷṛśṣḥ]", word.lower()):
            continue
        if LANGUAGE["code"] == "sa" and tok.startswith(("’", "‘", "'")) and not word.startswith("a"):
            word = "a" + word                                 # ’bhūt: the avagraha marks an elided a
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
                    tokens.append(Token(p, normalise(p), sub, _candidates_of(sub, p), src=surface))
                continue
        if a.headwords:
            cands = _candidates_of(a, surface)
            _fill_members(dpd, a, cands)
            split = a.best_split
            should_split = False
            if split is not None and len(split.parts) >= 2 and all(x.headwords for x in split.analyses):
                if not cands:
                    should_split = True
                elif getattr(dpd, "cologne", None) is not None or LANGUAGE.get("code") == "sa":
                    # In Sanskrit, split compounds combining names with titles or epithets (e.g. ārya + avalokiteśvara + bodhisattva)
                    cologne = getattr(dpd, "cologne", None)
                    has_name = any(x.headwords[0].kind == "name" or (cologne and cologne.is_name(x.key)) for x in split.analyses)
                    has_title = any(x.key in ("bodhisattva", "bodhisattvo", "mahāsattva", "tathāgata", "ārya", "bhagavat") for x in split.analyses)
                    if has_name and has_title and a.headwords[0].kind != "name":
                        should_split = True
            if should_split:
                for part in split.analyses:
                    tokens.append(Token(part.key, part.key, part, _candidates_of(part, part.key), src=surface))
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
                tokens.append(Token(part.key, part.key, part, _candidates_of(part, part.key), src=surface))
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

SYSTEM_TEMPLATE = (
    "You are a {lang} grammarian and a literal translator. For every word of a {lang} sentence you choose the one "
    "dictionary parse that the sentence requires, you gloss the word in that form, and you "
    "translate the sentence literally into normal English. You answer with JSON only."
)


# the author's rule of 2026-11-13 on words of address: one wording for the prompts of every stage
VOCATIVE_RULE = ("Every word of address (a word in the vocative case) is written in one of two ways only: a name, a title, "
                 "a kinship word or a customary form of address as the bare {lang} word; any other vocative, one that "
                 "describes the one addressed, as `source-word` (English), like `anagha` (faultless one), where the "
                 "backticks hold the {lang} word copied letter for letter as it stands and the parentheses hold the "
                 "English, never the reverse. Never turn a word of address into plain English, a relative clause or "
                 "square brackets, and never supply words such as '[you who are]'")
# Stage 1 only: the model there keeps to the rule above only with this curb; the later stages write technical terms in
# backticks as well and must not be told otherwise
BACKTICK_CURB = ("Backticks are for a describing word of address and for nothing else: every other noun, adjective, "
                 "participle or compound, in whatever case, is English only, with no {lang} beside it. Never write 'O' before a "
                 "word of address; a word of address that is not a name, a title, a kinship word or a customary form is always `word` (English)")


def vocative_rule() -> str:
    return VOCATIVE_RULE.format(lang=LANGUAGE["name"])


def backtick_curb() -> str:
    return BACKTICK_CURB.format(lang=LANGUAGE["name"])


def system_prompt() -> str:
    return SYSTEM_TEMPLATE.format(lang=LANGUAGE["name"])


def format_mantra(src: str, tr: str) -> str:
    """If a unit contains a mantra or dhāraṇī (e.g. ending in svāhā), format as: mantra (translation)."""
    if "svāhā" not in src.lower() and "svaha" not in src.lower():
        return tr
    m = re.search(r'\b((?:oṃ\s+|om\s+)?(?:gate\s+gate\s+pāragate\s+pārasaṃgate\s+bodhi\s+svāhā|[a-zāīūṛḷeaiouṃḥkgṅcjñṭḍṇtdnpbmyrlvśṣsh\s-]+svāhā))\b', src, re.I)
    if not m:
        return tr
    mantra = m.group(1).strip('- ')
    mantra = re.sub(r"^(?:tadyathā[-:\s]+)", "", mantra, flags=re.I).strip()
    if mantra.lower() in tr.lower():
        return tr
    intro_m = re.match(r'^(as follows:\s*|tadyathā:\s*|thus:\s*)?(.*)', tr, re.I)
    intro = (intro_m.group(1) or '') if intro_m else ''
    content = intro_m.group(2) if intro_m else tr
    content = content.strip(' .')
    if content.startswith('(') and content.endswith(')'):
        content = content[1:-1]
    return f"{intro}{mantra} ({content})."


_CITATION = r"[A-ZĀŚṚ][\w.]{0,12}"                                 # RV, AV, Kathās, TejobUp: where a sense is attested
CITATION_RE = re.compile(rf"^{_CITATION}$")
TRAILING_CITATION_RE = re.compile(rf",\s*{_CITATION}$")


def _shown_meaning(p: Parse) -> str:
    """A candidate's meaning as the prompt shows it: a Cologne entry without its headword echo, grammar tags and
    citations, and never the length of a dictionary column."""
    m = p.meaning or ""
    if LANGUAGE["code"] == "sa":
        parts = []
        for part in m.split(";"):                                     # (Parse.meaning holds at most three pieces)
            part = _clean_dict_gloss(part)
            part = re.sub(r"^\d+\.\s*", "", part)
            part = re.sub(r"^\S*[—˚]\S*\s+", "", part)                 # nir—vikalpa, pra-jñā—pāramitā: the headword again
            head, _, rest = part.partition(" ")
            if rest and head.replace("-", "") == p.lemma:
                part = rest
            part = TRAILING_CITATION_RE.sub("", part).strip(" ,")
            if part and not CITATION_RE.match(part):
                parts.append(part)
        m = "; ".join(parts) or m
    return (m[:157].rstrip() + "…") if len(m) > 160 else m


def prompt_for(unit_text: str, tokens: list[Token], glossary: dict[str, str], context: list[tuple[str, str]], initial_draft: str = "",
               whole: str = "") -> str:
    lines = [f"Sentence: {unit_text}"]
    if whole and whole.strip() != unit_text.strip():
        lines.append("\nThe sentence is one line of this verse, whose words construe together across its lines (translate only the "
                     f"sentence above, in the sense the whole verse gives it):\n{whole}")
    if initial_draft:
        lines.append(f"\nInitial draft translation from discourse context:\n\"{initial_draft}\"")
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
        said = None                                   # a headword's meaning once, not on each of its ten forms
        for c, p in enumerate(t.candidates, 1):
            meaning = _shown_meaning(p) or "—"
            lines.append(f"   {c}. {p.lemma} ({p.describe()})" + (f" — {meaning}" if (p.lemma, meaning) != said else " — 〃"))
            said = (p.lemma, meaning)
    present = terms_of(tokens)
    used = [f"{modern(k)} = {v}" for k, v in glossary.items() if v and k in present]
    rules = [
        "For every word choose the candidate whose grammatical form the sentence requires: an adjective or participle agrees with its noun in gender, number and case; the verb's person and number are its subject's; a locative absolute takes the locative participle.",
        "The gloss renders only that word in that form, in one to four English words, with the preposition the case needs where English needs one (\"by me\", \"in the night\", \"of the week\"), and no explanation.",
    ]
    epithets = vocative_rule() + "; its word gloss is the English alone."
    if LANGUAGE["code"] == "sa":
        rules.extend([
            f"Vocatives and honorifics must NOT be translated: in both word glosses and the sentence translation, leave any vocative address and any honorific untranslated as it stands in the text (e.g. Bhagavān, bhikṣavaḥ, āyuṣmān, bhadanta, Śāriputra, Maitreya; never 'the Blessed One', 'venerable', 'venerable sir', 'O monks', 'monks', etc.). Names stay in their {LANGUAGE['name']} stem form.",
            epithets,
            "The title of a text stays in its untranslated Sanskrit form, with its literal English translation in parentheses on first occurrence.",
            "A Buddhist technical term appears on its first use as `term` (English gloss), with the gloss the glossary gives; on subsequent uses, write the plain term.",
            "For a mantra or dhāraṇī, give the original text in italics followed by the English translation in parentheses: *mantra* (translation).",
        ])
    else:
        rules.append(f"Names stay in their {LANGUAGE['name']} stem form; honorifics and titles stay as they stand in the text (Bhagavā, bhikkhave, bhante). " + epithets)
    if PH_RE.search(unit_text):
        rules.append("The sentence contains placeholder markers of the form %%number%% (links, footnote marks, tags): reproduce every one of them exactly, once, in the translation, in the same position relative to the surrounding words, and never translate, renumber or drop one.")
    if initial_draft:
        rules.append("The sentence translation takes the initial draft as its baseline and improves it: correct any error against the dictionary candidates and the glossary, render every word and particle, and verify tense, aspect and case. Keep it natural, fluent, grammatical English, never a mechanical word-for-word calque: an aspectual or auxiliary idiom is rendered by the English tense it expresses, never by a tag in parentheses.")
    else:
        rules.append(f"The translation renders every word of the sentence, keeps a present-tense verb in the present, is rearranged into a normal English sentence, and adds nothing that the {LANGUAGE['name']} does not say.")
    if used:
        rules.append("These technical terms take these glosses: " + "; ".join(used) + ".")
    lines.append("\nRules:")
    lines.extend(f"{i}. {r}" for i, r in enumerate(rules, 1))
    lines.append('\nAnswer with JSON only, one entry per numbered word above, repeating the word, in this form: '
                 '{"words": [{"n": 1, "word": "evaṁ", "parse": 1, "gloss": "thus"}, {"n": 2, "word": "me", "parse": 3, "gloss": "by me"}], "translation": "…"}')
    return "\n".join(lines)


def _clean_quotes(s: str) -> str:
    """Unescape stray \\" and \\' sequences that the model sometimes emits around quoted speech in JSON."""
    s = re.sub(r'\\+(["\'])', r"\1", s)
    s = re.sub(r"\\+$", "", s)
    s = re.sub(r"\\\\+", "", s)
    return s.strip()


def _unescape_u(s: str) -> str:
    """Decode \\uXXXX escapes only; the rest of the string (IAST letters) is left as it is."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)


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
    words_list = data.get("words") if isinstance(data, dict) else None
    if not isinstance(words_list, list):
        words_list = []
    if not words_list:
        for m in re.finditer(r'\{[^{}]*"n"\s*:\s*\d+[^{}]*\}', text):
            try:
                words_list.append(json.loads(m.group(0)))
            except json.JSONDecodeError:
                continue
    choice: dict[int, int] = {}
    gloss: dict[int, str] = {}
    surfaces = [normalise(getattr(t, "surface", "") or "") for t in tokens]
    cursor = 0
    for w in words_list:
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
                gloss[n] = _clean_quotes(g)
    translation = data.get("translation", "") if isinstance(data, dict) else ""
    if isinstance(translation, list):                                  # a verse answered as a list of lines
        translation = " ".join(str(x) for x in translation)
    elif not isinstance(translation, str):
        translation = ""
    if not translation:
        m_full = re.search(r'"translation"\s*:\s*"(.*)"\s*\}', text, re.S)
        if m_full:
            raw_tr = m_full.group(1)
            translation = _unescape_u(raw_tr)
        else:
            for m in re.finditer(r'"translation"\s*:\s*"((?:[^"\\]|\\.)*)"', text):
                translation = _unescape_u(m.group(1))
    return choice, gloss, _clean_quotes(translation or "")


# --------------------------------------------------------------------------------------
# Units and the document
# --------------------------------------------------------------------------------------


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


SOURCE_LETTER_RE = re.compile(r"[āīūṃṁṅñṭḍṇḷṛṝśṣḥ]", re.I)


def is_source(dpd, text: str) -> bool:
    """Should this block be translated? A block is left alone only on evidence that it is not the source
    language: a grammar's sandhi-laden line is still Pāli though the lexicon knows half its words."""
    words = [w for w, _, p in tokenise(text) if not p]
    if not words:
        return False
    if sum(1 for w in words if w.lower() in ENGLISH_STOP) / len(words) >= 0.2:
        return False                                        # English prose, an admonition's caption
    if SOURCE_LETTER_RE.search(text):
        return True
    return sum(1 for w in words if dpd.known(normalise(w))) / len(words) >= 0.5   # "Namo tassa", not "Meaning"


def units_pieces(text: str, segments: list[tuple[str, str]] | None, para_no: int, seg_pos: int) -> tuple[list[tuple[str, str]], int, bool]:
    """The (number, source) pieces of one paragraph; (pieces, next segment position, verse?)."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    verse = len(lines) > 1 and all(len(ln.split()) <= 12 for ln in lines)
    pieces: list[tuple[str, str]] = []
    if segments:
        m = match_segments(text, segments, seg_pos)
        if m:
            pieces, seg_pos = m
    if not pieces:
        parts = [ln.strip() for ln in lines] if verse else split_sentences(" ".join(lines))
        parts = [x for x in parts if re.search(r"[^\W\d_]", x)]      # "| ||": a piece of punctuation alone is no unit
        pieces = [(f"{para_no}.{i}", x) for i, x in enumerate(parts, 1)]
    return pieces, seg_pos, verse
