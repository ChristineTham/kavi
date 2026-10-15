"""Digital Pāḷi Dictionary access.

Every inflected form is looked up in the DPD's ``lookup`` table (1.28 million forms), which gives its
headwords, its grammatical parses (gender, case, number; tense, person, number) and the DPD
deconstructor's sandhi and compound splits. A form the table lacks is split with the full deconstructor
output (``deconstructor_output.json``, indexed once into ``deconstructor.sqlite``) and, failing that,
with the reverse-sandhi heuristics in :mod:`kavi.sandhi`, and each part is looked up in turn.

The database is the DPD's own ``dpd.db`` (CC BY-NC-SA 4.0, Bodhirasa Bhikkhu, https://www.dpdict.net/),
opened read-only. Nothing from it is reproduced beyond the entries consulted for the text at hand.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .glossary import classify, honorific_form, term_form

GENDER = {"masc": "masculine", "fem": "feminine", "nt": "neuter", "x": "any gender"}
CASE = {"nom": "nominative", "acc": "accusative", "instr": "instrumental", "dat": "dative", "abl": "ablative",
        "gen": "genitive", "loc": "locative", "voc": "vocative"}
NUMBER = {"sg": "singular", "pl": "plural", "dual": "dual"}
TENSE = {"pr": "present", "aor": "aorist (past)", "imp": "imperative", "opt": "optative", "fut": "future",
         "imperf": "imperfect", "perf": "perfect", "cond": "conditional"}
PERSON = {"1st": "1st person", "2nd": "2nd person", "3rd": "3rd person"}
OTHER = {"reflx": "reflexive (attanopada)"}
POS = {
    "abs": "absolutive", "adj": "adjective", "aor": "aorist verb", "card": "cardinal number", "cond": "conditional verb",
    "cs": "conjugational sign", "fem": "feminine noun", "fut": "future verb", "ger": "gerund", "idiom": "idiom",
    "imp": "imperative verb", "imperf": "imperfect verb", "ind": "indeclinable", "inf": "infinitive", "letter": "letter",
    "masc": "masculine noun", "nt": "neuter noun", "opt": "optative verb", "ordin": "ordinal number",
    "perf": "perfect verb", "pp": "past participle", "pr": "present-tense verb", "prefix": "prefix", "pron": "pronoun",
    "prp": "present participle", "ptp": "potential participle", "root": "root", "sandhi": "sandhi form",
    "suffix": "suffix", "ve": "verbal ending",
}
NOUN_POS = {"masc", "fem", "nt", "pp", "prp", "ptp", "adj", "card", "ordin", "pron", "noun"}
VERB_POS = {"pr", "aor", "fut", "imp", "opt", "perf", "imperf", "cond", "verb"}
INDECL_POS = {"ind", "prefix", "sandhi", "particle", "suffix", "idiom", "letter", "cs", "ve", "abbrev", "inf", "abs"}

PUNCT = "‘’“”\"'.,;:?!()[]{}|*_`«»‹›=+/\\"


ABBREV = {**GENDER, **CASE, **NUMBER, **TENSE, **PERSON, **OTHER, "pp": "past participle", "prp": "present participle",
          "ptp": "potential participle", "abs": "absolutive", "adj": "adjective", "ind": "indeclinable", "adv": "adverb",
          "comp": "compound", "abstr": "abstract noun", "caus": "causative", "pass": "passive", "compar": "comparative",
          "superl": "superlative", "deno": "denominative", "desid": "desiderative", "intens": "intensive",
          "impers": "impersonal", "emph": "emphatic", "interj": "interjection", "conj": "conjunction", "prep": "preposition",
          "neg": "negative", "inf": "infinitive", "ger": "gerund", "pron": "pronoun", "card": "cardinal", "ordin": "ordinal"}
ABBREV_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, ABBREV), key=len, reverse=True)) + r")\b")


def parse_words(parse: str) -> str:
    """'masc nom sg' -> 'masculine nominative singular'; 'pr 3rd sg' -> 'present 3rd person singular';
    also 'voc pl of bhikkhu' -> 'vocative plural of bhikkhu'."""
    return ABBREV_RE.sub(lambda m: ABBREV[m.group(1)], parse)


def pos_compatible(parse_pos: str, hw_pos: str) -> bool:
    if parse_pos == hw_pos:
        return True
    if parse_pos == "noun":
        return hw_pos in ("masc", "fem", "nt")
    if parse_pos == "verb":
        return hw_pos in VERB_POS
    return False


def lemma_clean(lemma: str) -> str:
    return re.sub(r" \d[\d.]*$", "", lemma)


def normalise(word: str) -> str:
    return word.lower().replace("ṁ", "ṃ").strip(PUNCT + "-–—")


@dataclass
class Headword:
    id: int
    lemma: str
    stem: str
    pos: str
    grammar: str
    meaning: str
    meaning_lit: str
    meaning_2: str
    construction: str
    root: str
    root_meaning: str
    family_set: str
    plus_case: str
    compound_type: str = ""                            # dvanda, kammadhāraya, tappurisa … (DPD)
    compound_construction: str = ""                    # the DPD's compound analysis, members with endings in <b>…</b>
    parses: list[str] = field(default_factory=list)   # raw DPD parses of the looked-up form, e.g. "masc nom sg"
    ebt_count: int = 0                                 # occurrences in the early Buddhist texts (DPD)
    kind: str = ""                                     # 'name' | 'honorific' | 'technical' | 'name?' | ''

    @property
    def pos_full(self) -> str:
        base = POS.get(self.pos, self.pos)
        extra = self.grammar
        if extra and extra != self.pos:
            # "pp of karoti", "adj, from na kata", "voc pl of bhikkhu": keep the informative tail, in words
            tail = re.sub(r"^(?:%s)(?:,\s*)?" % re.escape(self.pos), "", extra).strip(", ")
            if tail:
                base += f" ({parse_words(tail)})"
        return base

    @property
    def analysis(self) -> str:
        """Part of speech plus the parse(s) of the form, in words."""
        parses = " | ".join(dict.fromkeys(parse_words(p) for p in self.parses))
        return f"{self.pos_full}; {parses}" if parses else self.pos_full

    @property
    def gloss(self) -> str:
        m = self.meaning or self.meaning_2 or "—"
        if self.meaning_lit:
            m += f" [lit. {self.meaning_lit}]"
        return m


@dataclass
class Split:
    parts: list[str]
    source: str                       # 'lookup' | 'deconstructor' | 'sandhi'
    analyses: list["Analysis"] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " + ".join(self.parts)

    @property
    def complete(self) -> bool:
        return all(a.headwords for a in self.analyses)


@dataclass
class Analysis:
    surface: str
    key: str
    capitalised: bool = False
    found: bool = False
    stem_only: bool = False           # the word is a bare stem (a headword), not an inflected form
    headwords: list[Headword] = field(default_factory=list)
    splits: list[Split] = field(default_factory=list)
    note: str = ""
    name_hint: bool = False

    def governing(self, glossary: dict[str, str] | None = None) -> "Headword | None":
        """The headword whose kind decides the rendering: the first (most used) headword if it has a kind or a
        glossary entry; else the first of the next two that has a kind (a name or honorific hidden behind a
        common homonym); else the first. A glossary entry never overrides a commoner ordinary sense."""
        if not self.headwords:
            return None
        first = self.headwords[0]
        if first.kind or (glossary and first.stem in glossary):
            return first
        for h in self.headwords[1:3]:
            if h.kind == "honorific" or (h.kind == "name" and self.capitalised):
                return h
        return first

    @property
    def best_split(self) -> Split | None:
        for s in self.splits:
            if s.complete:
                return s
        return self.splits[0] if self.splits else None

    @property
    def kinds(self) -> set[str]:
        k = {h.kind for h in self.headwords if h.kind}
        for s in self.splits[:1]:
            for a in s.analyses:
                k |= a.kinds
        return k


class DPD:
    def __init__(self, db_path: Path, decon_db: Path | None = None, decon_json: Path | None = None):
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"dpd.db not found at {db_path}")
        self.con = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
        self.con.row_factory = sqlite3.Row
        self.decon = self._open_decon(decon_db, decon_json)
        self._hw: dict[int, sqlite3.Row | None] = {}
        self._root: dict[str, sqlite3.Row | None] = {}
        self._lookup: dict[str, sqlite3.Row | None] = {}
        self._analysis: dict[str, Analysis] = {}
        self.version = self._version()

    # -- raw access -----------------------------------------------------------------

    def _version(self) -> str:
        try:
            row = self.con.execute("select value from db_info where key='dpd_release_version'").fetchone()
            return row[0] if row else ""
        except sqlite3.Error:
            return ""

    @staticmethod
    def _open_decon(decon_db: Path | None, decon_json: Path | None):
        if decon_db and decon_db.exists():
            return sqlite3.connect(f"file:{decon_db}?immutable=1", uri=True)
        if decon_json and decon_json.exists():
            target = decon_db or decon_json.with_suffix(".sqlite")
            print(f"indexing {decon_json.name} into {target.name} (once) …", file=sys.stderr)
            data = json.loads(decon_json.read_text(encoding="utf-8"))
            con = sqlite3.connect(target)
            con.execute("create table if not exists decon (word text primary key, splits text not null)")
            con.executemany("insert or replace into decon values (?, ?)",
                            ((k, json.dumps(v, ensure_ascii=False)) for k, v in data.items()))
            con.commit()
            con.close()
            return sqlite3.connect(f"file:{target}?immutable=1", uri=True)
        return None

    def lookup(self, key: str):
        if key not in self._lookup:
            self._lookup[key] = self.con.execute(
                "select lookup_key, headwords, roots, deconstructor, variant, see, spelling, grammar "
                "from lookup where lookup_key=?", (key,)).fetchone()
        return self._lookup[key]

    def headwords_by_lemma(self, stem: str) -> list[int]:
        rows = self.con.execute(
            "select id from dpd_headwords where lemma_1 = ? or lemma_1 glob ? order by lemma_1",
            (stem, stem + " [0-9]*")).fetchall()
        return [r[0] for r in rows]

    def deconstruct(self, key: str) -> list[str]:
        if self.decon is None:
            return []
        row = self.decon.execute("select splits from decon where word=?", (key,)).fetchone()
        return json.loads(row[0]) if row else []

    def headword_row(self, hid: int):
        if hid not in self._hw:
            self._hw[hid] = self.con.execute(
                "select id, lemma_1, pos, grammar, verb, meaning_1, meaning_lit, meaning_2, construction, root_key, "
                "family_set, plus_case, ebt_count, compound_type, compound_construction from dpd_headwords where id=?",
                (hid,)).fetchone()
        return self._hw[hid]

    def root(self, key: str):
        if key not in self._root:
            self._root[key] = self.con.execute(
                "select root, root_group, root_sign, root_meaning from dpd_roots where root=?", (key,)).fetchone()
        return self._root[key]

    def known(self, key: str) -> bool:
        """Is this a word the DPD can gloss (an inflected form or a bare headword)?"""
        row = self.lookup(key)
        if row is not None and row["headwords"]:
            return True
        return bool(self.headwords_by_lemma(key))

    def frequency(self, key: str) -> float:
        """How often the texts use this form: the largest ebt_count among its headwords."""
        row = self.lookup(key)
        hids = json.loads(row["headwords"]) if row is not None and row["headwords"] else self.headwords_by_lemma(key)
        best = 0
        for hid in hids[:6]:
            hw = self.headword_row(hid)
            if hw is not None and (hw["ebt_count"] or 0) > best:
                best = hw["ebt_count"]
        return float(best)

    # -- analysis ---------------------------------------------------------------------

    def _headwords(self, row, key: str, mid_capital: bool = False) -> list[Headword]:
        hids = json.loads(row["headwords"]) if row["headwords"] else []
        parses = json.loads(row["grammar"]) if row["grammar"] else []
        out = []
        for hid in hids:
            hw = self.headword_row(hid)
            if hw is None:
                continue
            stem = lemma_clean(hw["lemma_1"])
            my_parses = [p[2] for p in parses if p[0] == stem and pos_compatible(p[1], hw["pos"])]
            root_meaning = ""
            if hw["root_key"]:
                r = self.root(hw["root_key"])
                if r:
                    root_meaning = f"{r['root']} {r['root_meaning']}"
            meaning = hw["meaning_1"] or hw["meaning_2"] or ""
            out.append(Headword(
                id=hid, lemma=hw["lemma_1"], stem=stem, pos=hw["pos"], grammar=hw["grammar"] or "",
                meaning=meaning, meaning_lit=hw["meaning_lit"] or "", meaning_2=hw["meaning_2"] or "",
                construction=(hw["construction"] or "").replace("\n", " | "), root=hw["root_key"] or "",
                root_meaning=root_meaning, family_set=hw["family_set"] or "", plus_case=hw["plus_case"] or "",
                compound_type=hw["compound_type"] or "", compound_construction=hw["compound_construction"] or "",
                parses=my_parses, ebt_count=hw["ebt_count"] or 0,
                kind=classify(stem, meaning, hw["family_set"] or ""),
            ))
        # the headword spelt like the form first (vā before va), then the ones the texts use most; a name spelt like
        # the form (dhammā, the nun) comes first only when the text capitalises the word inside a sentence
        out.sort(key=lambda h: (0 if h.stem == key and (h.kind != "name" or mid_capital) else 1, -h.ebt_count))
        return out

    def analyse(self, surface: str, depth: int = 0, mid_capital: bool = False) -> Analysis:
        """``mid_capital``: the word is capitalised although it does not open a sentence (a hint of a name)."""
        key = normalise(surface)
        cache_key = f"{key}\x00{mid_capital}\x00{depth}"
        if cache_key in self._analysis:
            return self._analysis[cache_key]
        res = Analysis(surface=surface, key=key, capitalised=mid_capital)
        if not key:
            return res
        if "’" in key or "'" in key:                       # vā’tave: an apostrophe marks an elided vowel
            parts = [p for p in re.split(r"[’']", key) if p]
            if len(parts) > 1 and depth == 0:
                res.splits.append(Split(parts, "elision", [self.analyse(p, 1) for p in parts]))
                res.found = True
                self._analysis[cache_key] = res
                return res
        row = self.lookup(key)
        splits: list[tuple[str, str]] = []
        if row is not None:
            res.found = True
            res.headwords = self._headwords(row, key, mid_capital)
            notes = []
            if row["spelling"]:
                notes.append("spelling: " + ", ".join(json.loads(row["spelling"])))
            if row["see"]:
                notes.append("see: " + ", ".join(json.loads(row["see"])))
            res.note = "; ".join(notes)
            splits = [(s, "lookup") for s in (json.loads(row["deconstructor"]) if row["deconstructor"] else [])]
        if row is None or not res.headwords:
            hids = self.headwords_by_lemma(key)
            if hids:
                fake = {"headwords": json.dumps(hids), "grammar": "", "lookup_key": key}
                res.found = True
                res.stem_only = True
                res.headwords = self._headwords(fake, key, mid_capital)
        if depth == 0 and not res.headwords:
            from .sandhi import lengthened_variant, rank_splits, split as sandhi_split
            if not splits:
                splits = [(s, "deconstructor") for s in self.deconstruct(key)]
            ours = [(" + ".join(parts), "sandhi") for parts in sandhi_split(key, self.known, self.frequency)]
            sources = {s: src for s, src in ours}
            sources.update({s: src for s, src in splits})          # the DPD's own split keeps its label
            curated = {s for s, src in splits}
            ranked = rank_splits([[normalise(p) for p in s.split(" + ")] for s in sources], self.known, self.frequency, curated)
            splits = [(" + ".join(parts), sources.get(" + ".join(parts), "sandhi")) for parts in ranked[:4]]
            short = lengthened_variant(key, self.known)
            if short:                                                  # khāyatī -> khāyati: the word itself, lengthened
                splits.insert(0, (short, "lengthened final (§15)"))
        if depth == 0:
            for s, source in splits:
                parts = [normalise(p) for p in s.split(" + ")]
                if len(parts) == 1 and parts[0] == key:
                    continue
                res.splits.append(Split(parts, source, [self.analyse(p, 1) for p in parts]))
            if res.splits:
                res.found = True
        if mid_capital and not res.headwords and not any(s.complete for s in res.splits):
            res.name_hint = True                       # an unknown capitalised word inside a sentence: probably a name
        self._analysis[cache_key] = res
        return res


# ------------------------------------------------------------------------------------------
# Tokenising and rendering
# ------------------------------------------------------------------------------------------

WORD_RE = re.compile(r"[A-Za-zĀāĪīŪūṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷ’']+")


SENTENCE_START_RE = re.compile(r"(?:^|[.?!।॥—–\-:;\n]|[\[(“‘\"'*_#>|]|^\s*\d+\.)\s*$")


def _clean(text: str) -> str:
    text = re.sub(r"\[\^[^\]]+\]", " ", text)                 # footnote markers
    text = re.sub(r"!?\[[^\]]*\]\([^)]*\)", " ", text)          # links
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"%%\d+%%", " ", text)                        # placeholders
    return text.replace("ṁ", "ṃ")


def tokens_with_position(text: str) -> list[tuple[str, bool]]:
    """(word, mid_capital) for every Pāḷi word: mid_capital when the word is capitalised but does not open a
    sentence, a quotation, a line or a list item — the way Roman-script editions mark proper names."""
    text = _clean(text)
    out = []
    for m in WORD_RE.finditer(text):
        w = m.group(0).strip("’'")
        if not w or not re.search(r"[a-zāīūṃṅñṭḍṇḷ]", w.lower()):
            continue
        before = text[max(0, m.start() - 12): m.start()]
        opens = not before.strip() or bool(SENTENCE_START_RE.search(before))
        out.append((w, w[:1].isupper() and not opens))
    return out


def tokens(text: str) -> list[str]:
    """The Pāḷi words of a text, in order (punctuation and markup dropped)."""
    return [w for w, _ in tokens_with_position(text)]


def unique_tokens(text: str) -> list[str]:
    return [w for w, _ in unique_words(text)]


def unique_words(text: str) -> list[tuple[str, bool]]:
    """Each distinct word once, with True if any occurrence is capitalised inside a sentence."""
    order: dict[str, int] = {}
    out: list[list] = []
    for w, mid in tokens_with_position(text):
        k = normalise(w)
        if k not in order:
            order[k] = len(out)
            out.append([w, mid])
        elif mid:
            out[order[k]][1] = True
    return [(w, m) for w, m in out]


def analyse_text(dpd: "DPD", text: str) -> list[Analysis]:
    return [dpd.analyse(w, mid_capital=mid) for w, mid in unique_words(text)]


def _cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def diverse_headwords(headwords: list[Headword], n: int) -> list[Headword]:
    """The first ``n`` headwords, but with every part of speech represented once before homonyms of the same
    class repeat — so a pronoun (assa "to him") is not hidden behind an optative and three nouns."""
    if len(headwords) <= n:
        return headwords
    chosen: list[Headword] = []
    seen_pos: set[str] = set()
    for h in headwords:
        if h.pos not in seen_pos:
            chosen.append(h)
            seen_pos.add(h.pos)
        if len(chosen) == n:
            break
    for h in headwords:
        if len(chosen) == n:
            break
        if h not in chosen:
            chosen.append(h)
    return sorted(chosen, key=headwords.index)


def analysis_rows(a: Analysis, max_hw: int = 3) -> list[tuple[str, str, str]]:
    """(word, grammar, meaning) rows for one analysed word, sub-rows for a sandhi/compound split."""
    rows: list[tuple[str, str, str]] = []
    if a.headwords:
        shown = diverse_headwords(a.headwords, max_hw)
        for h in shown:
            rows.append((a.surface, f"{h.lemma}: {h.analysis}", h.gloss))
        if len(a.headwords) > len(shown):
            rows.append((a.surface, f"… {len(a.headwords) - len(shown)} more homonyms", ""))
    split = a.best_split
    if split is not None and not a.headwords:
        label = {"elision": "elided vowel", "lengthened final (§15)": "final vowel lengthened before ti"}.get(split.source, "sandhi/compound")
        rows.append((a.surface, f"= {split.text}", label))
        for part in split.analyses:
            if part.headwords:
                for h in diverse_headwords(part.headwords, max_hw):
                    rows.append((f"↳ {part.key}", f"{h.lemma}: {h.analysis}", h.gloss))
            else:
                rows.append((f"↳ {part.key}", "—", "not in DPD"))
    if not rows:
        rows.append((a.surface, "—", "not in DPD"))
    return rows


def analysis_table(analyses: list[Analysis], max_hw: int = 3) -> str:
    out = ["| Word | Grammar (DPD) | Meaning |", "| --- | --- | --- |"]
    for a in analyses:
        for w, g, m in analysis_rows(a, max_hw):
            out.append(f"| {_cell(w)} | {_cell(g)} | {_cell(m)} |")
    return "\n".join(out)


def _rendering(h: Headword, surface: str, glossary: dict[str, str] | None = None) -> str:
    """How the word should come out in English, by its kind: a name is left in its stem form, an honorific is
    left as it stands in the text, a technical term is shown as it stands in backticks with its gloss; anything
    else gets its DPD meanings."""
    meaning = h.meaning or h.meaning_2 or "—"
    surface = surface.strip("’'")
    gloss = (glossary or {}).get(h.stem)
    if gloss:
        form = term_form(h.stem, surface, h.parses)
        return f"`{form}` ({gloss}) [a technical term, kept in Pāli with this gloss on first use, then '{gloss}'; {h.analysis}]"
    if h.kind == "name":
        return f"{h.stem.capitalize()} [a name, left untranslated: {meaning}; {h.analysis}]"
    if h.kind == "honorific":
        form = honorific_form(h.stem, surface, h.parses, h.family_set)
        return f"{form} [an honorific, left untranslated: {meaning}; {h.analysis}]"
    if h.kind == "technical":
        form = term_form(h.stem, surface, h.parses)
        return f"`{form}` ({meaning.split(';')[0].strip()}) [if used as a technical term; otherwise {meaning}; {h.analysis}]"
    return f"{meaning} [{h.stem}, {h.analysis}]"


def reference_pairs(analyses: list[Analysis], max_hw: int = 2, glossary: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """(source, gloss) pairs in the form the translate model's in-context mode expects."""
    pairs = []
    for a in analyses:
        if a.headwords:
            g = a.governing(glossary)
            hws = [g] + [h for h in a.headwords if h is not g]
            pairs.append((a.surface, "; or ".join(_rendering(h, a.surface, glossary) for h in hws[:max_hw])))
        elif a.best_split is not None:
            parts = []
            for part in a.best_split.analyses:
                if part.headwords:
                    parts.append(f"{part.key} = {_rendering(part.headwords[0], part.key, glossary)}")
                else:
                    parts.append(f"{part.key} = ?")
            pairs.append((a.surface, "(" + a.best_split.text + ") " + "; ".join(parts)))
        elif a.name_hint:
            pairs.append((a.surface, f"{a.surface.strip(chr(8217))} [probably a name, left untranslated]"))
    return pairs


def special_words(analyses: list[Analysis], glossary: dict[str, str] | None = None) -> dict[str, list[tuple[str, str]]]:
    """Names, honorifics and technical terms found in the text: {kind: [(surface, rendering), …]} — a name's
    rendering is its stem, an honorific's the word as it stands, a technical term's "`word` (gloss)"."""
    out: dict[str, list[tuple[str, str]]] = {"name": [], "honorific": [], "technical": []}
    seen: set[tuple[str, str]] = set()
    glossary = glossary or {}

    def add(kind: str, surface: str, h: Headword):
        surface = surface.strip("’'")
        if h.stem in glossary:
            kind, item = "technical", (surface, f"`{term_form(h.stem, surface, h.parses)}` ({glossary[h.stem]})")
        elif kind == "technical":
            item = (surface, f"`{term_form(h.stem, surface, h.parses)}` ({(h.meaning or h.meaning_2).split(';')[0].strip()})")
        elif kind == "honorific":
            item = (surface, honorific_form(h.stem, surface, h.parses, h.family_set))
        else:
            item = (surface, h.stem.capitalize())
        if (kind, item[0]) not in seen:
            seen.add((kind, item[0]))
            out[kind].append(item)

    for a in analyses:
        h = a.governing(glossary)
        if h is not None and (h.kind or h.stem in glossary):
            add(h.kind, a.surface, h)
        if not a.headwords and a.best_split:
            for part in a.best_split.analyses:
                h = part.governing(glossary)
                if h is not None and (h.kind or h.stem in glossary):
                    add(h.kind, part.key, h)
        if a.name_hint and ("name", a.surface) not in seen:
            seen.add(("name", a.surface))
            out["name"].append((a.surface, a.surface.strip("’'")))
    return out
