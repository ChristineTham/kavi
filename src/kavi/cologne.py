"""The Cologne Digital Sanskrit Dictionaries as a local SQLite file.

Cologne (https://www.sanskrit-lexicon.uni-koeln.de/) publishes each dictionary as a text file in a documented
markup (``<abbr>-meta2.txt`` beside it): an entry runs from a meta line ``<L>id<pc>page,col<k1>KEY<k2>KEY2[<h>N][<e>N]``
to ``<LEND>``; ``k1`` is the headword in SLP1, ``k2`` the printed spelling. Kavi uses three of them for Sanskrit and
Buddhist Hybrid Sanskrit: ``bhs`` (Edgerton, Buddhist Hybrid Sanskrit Dictionary, 1953), ``mw`` (Monier-Williams,
1899) and ``ap90`` (Apte, 1890). ``build()`` reads the files in ``<data_dir>/cologne/`` and writes
``<data_dir>/sanskrit.sqlite`` with the cleaned text of every entry, its headword in SLP1 and IAST, the part of
speech the dictionary prints and the Pāḷi cognate Edgerton gives. The digitisations are the Sanskrit Library's
and Thomas Malten's, CC BY-NC-SA 3.0; nothing is reproduced beyond the entries consulted for the text at hand.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterator

SOURCES = ("bhs", "mw", "ap90")
RAW = "https://raw.githubusercontent.com/sanskrit-lexicon/csl-orig/main/v02/{d}/{d}.txt"

# SLP1 -> IAST (vidyut-lipi does the same, but the parser should not need it)
_SLP1 = {
    "A": "ā", "I": "ī", "U": "ū", "f": "ṛ", "F": "ṝ", "x": "ḷ", "X": "ḹ", "E": "ai", "O": "au", "M": "ṃ", "H": "ḥ",
    "K": "kh", "G": "gh", "N": "ṅ", "C": "ch", "J": "jh", "Y": "ñ", "w": "ṭ", "W": "ṭh", "q": "ḍ", "Q": "ḍh", "R": "ṇ",
    "T": "th", "D": "dh", "P": "ph", "B": "bh", "S": "ś", "z": "ṣ", "~": "̃",
}


def slp1_to_iast(s: str) -> str:
    return "".join(_SLP1.get(ch, ch) for ch in s)


META_RE = re.compile(r"^<L>(?P<L>[^<]*)<pc>(?P<pc>[^<]*)<k1>(?P<k1>[^<]*)<k2>(?P<k2>[^<]*)(?:<h>(?P<h>[^<]*))?(?:<e>(?P<e>[^<]*))?")


def iter_entries(path: Path) -> Iterator[dict]:
    """The entries of one Cologne text file: meta fields and the raw body."""
    meta: dict | None = None
    body: list[str] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("<L>"):
                m = META_RE.match(line)
                meta = m.groupdict() if m else None
                body = []
            elif line.startswith("<LEND>"):
                if meta is not None:
                    yield {**meta, "body": "\n".join(body)}
                meta = None
            elif meta is not None:
                body.append(line)


_TAG_S = re.compile(r"<s>(.*?)</s>")                       # Sanskrit in SLP1 (MW)
_TAG_S1 = re.compile(r"<s1[^>]*>(.*?)</s1>")                # Sanskrit already in IAST (MW)
_TAG_AB_N = re.compile(r'<ab n="([^"]*)"[^>]*>(.*?)</ab>')  # abbreviation with its expansion
_TAG_LEX = re.compile(r"<lex[^>]*>(.*?)</lex>")
_TAG_DIV = re.compile(r"<div n=\"[^\"]*\"\s*/>")
_TAG_SELF = re.compile(r"<[a-zA-Z][^<>]*/>")
_TAG_ANY = re.compile(r"</?[a-zA-Z][^<>]*>")
_AP_S = re.compile(r"\{#(.*?)#\}", re.S)                      # Sanskrit in SLP1 (Apte)
_AP_CODE = re.compile(r"\{(?:c\d+c|L[a-z]+|\d+|[a-z]+\d*)\}")       # Apte's layout codes
_BOLD = re.compile(r"\{@(.*?)@\}", re.S)
_ITAL = re.compile(r"\{%(.*?)%\}", re.S)
_PAGE = re.compile(r"\[Page[^\]]*\]")
_PALI = re.compile(r"\(=\s*Pali\s+([^;,)]+)")             # Edgerton's "(= Pali satta)"
_SPACE = re.compile(r"[ \t]+")


def clean_body(body: str, source: str) -> tuple[str, str, str]:
    """(text, lex, pali): the entry's text with the markup removed (Sanskrit in IAST), the grammatical label the
    dictionary prints (``m.``, ``f.``, ``n.``, ``adj.``, ``ind.``, ``P. A.``) and Edgerton's Pāḷi cognate."""
    text = _PAGE.sub("", body)
    lexes = _TAG_LEX.findall(text)
    text = _TAG_S.sub(lambda m: slp1_to_iast(m.group(1)).replace("/", "").replace("\\", ""), text)
    text = _TAG_S1.sub(lambda m: m.group(1), text)
    text = _TAG_AB_N.sub(lambda m: m.group(1), text)
    text = _TAG_DIV.sub(" ", text)
    text = _AP_S.sub(lambda m: slp1_to_iast(m.group(1)), text)
    text = _AP_CODE.sub("", text)
    text = _BOLD.sub(lambda m: m.group(1), text)
    text = _ITAL.sub(lambda m: m.group(1), text)
    text = _TAG_SELF.sub("", text)
    text = _TAG_ANY.sub("", text)
    pali = ""
    m = _PALI.search(text)
    if m:
        pali = m.group(1).strip().strip("˚°-")
    text = text.replace("¦", "").replace("\n", " ")
    text = _SPACE.sub(" ", text).strip(" ;,")
    lex = "; ".join(dict.fromkeys(l.strip() for l in lexes if l.strip()))
    return text, lex, pali


def build(data_dir: Path, sources: tuple[str, ...] = SOURCES, progress=None) -> Path:
    """Write ``<data_dir>/sanskrit.sqlite`` from the Cologne text files in ``<data_dir>/cologne/``."""
    data_dir = Path(data_dir)
    out = data_dir / "sanskrit.sqlite"
    tmp = out.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE entries (source TEXT, L TEXT, k1 TEXT, iast TEXT, k2 TEXT, hom TEXT, lex TEXT, body TEXT, pali TEXT, page TEXT)")
    n = 0
    for src in sources:
        path = data_dir / "cologne" / f"{src}.txt"
        if not path.exists():
            if progress:
                progress(f"{src}.txt not found, skipped")
            continue
        rows = []
        for e in iter_entries(path):
            text, lex, pali = clean_body(e["body"], src)
            k1 = (e["k1"] or "").strip()
            rows.append((src, e["L"], k1, slp1_to_iast(k1), (e["k2"] or "").strip(), e.get("h") or "", lex, text, pali, e["pc"]))
            if len(rows) >= 5000:
                con.executemany("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
                n += len(rows)
                rows = []
        con.executemany("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        n += len(rows)
        if progress:
            progress(f"{src}: {n} entries so far")
    con.execute("CREATE INDEX ix_k1 ON entries (k1)")
    con.execute("CREATE INDEX ix_iast ON entries (iast)")
    con.execute("CREATE INDEX ix_source ON entries (source)")
    con.execute("CREATE INDEX ix_L ON entries (source, L)")
    con.commit()
    resolve_references(con)
    con.close()
    if out.exists():
        out.unlink()
    tmp.rename(out)
    return out


_REF = re.compile(r"^\{\{Lbody=(\d+)\}\}$")
_CLASS_NASAL = {"k": "ṅ", "kh": "ṅ", "g": "ṅ", "gh": "ṅ", "c": "ñ", "ch": "ñ", "j": "ñ", "jh": "ñ", "ṭ": "ṇ", "ṭh": "ṇ", "ḍ": "ṇ", "ḍh": "ṇ",
                "t": "n", "th": "n", "d": "n", "dh": "n", "p": "m", "ph": "m", "b": "m", "bh": "m"}


def nasal_variants(iast: str) -> list[str]:
    """The spellings of a word with anusvāra for a class nasal before a stop and the reverse: saṅgati, saṃgati, sambodhi."""
    out: list[str] = []
    a = re.sub(r"[ṅñṇnm](?=[kgcjṭḍtdpb])", "ṃ", iast)
    if a != iast:
        out.append(a)
    b = re.sub(r"ṃ(?=([kgcjṭḍtdpb]h?))", lambda m: _CLASS_NASAL[m.group(1)], iast)
    if b != iast and b not in out:
        out.append(b)
    return out


def resolve_references(con: sqlite3.Connection) -> int:
    """A body that is only ``{{Lbody=N}}`` ("the same as entry N", 7,500 of them, Apte's and Monier-Williams'
    cross-references) is replaced by entry N's body; a chain of references is followed."""
    n = 0
    for _ in range(4):
        rows = con.execute("SELECT rowid, source, body FROM entries WHERE body LIKE '{{Lbody=%'").fetchall()
        if not rows:
            break
        for rowid, source, body in rows:
            m = _REF.match(body.strip())
            if not m:
                continue
            target = con.execute("SELECT body FROM entries WHERE source = ? AND L = ?", (source, m.group(1))).fetchone()
            if target and target[0] != body:
                con.execute("UPDATE entries SET body = ? WHERE rowid = ?", (target[0], rowid))
                n += 1
        con.commit()
    return n


_GENDER_MW = re.compile(r"^(?:\d\. )?\S+ (?:\([^)]*\),? )?(?:\d\. )?(mfn|mf\([^)]{1,12}\)n|m\. n|m\. f|f\. n|m|f|n|ind\.p|ind)\.(?= |$)")


def _g(label: str) -> str:
    """The gender words for a dictionary label: ``mf(atī)n`` (yāvat) is an adjective like ``mfn``."""
    return "adj" if label.startswith("mf(") else _GENDER[label]
_LETTER = re.compile(r"\bthe \d+(?:st|nd|rd|th) (?:consonant|letter|vowel)\b")
_GENDER_BHS = re.compile(r"^(?:\d+ )?\S+,? (?:\([^)]*\),? )?(?:normally |usually |regularly |generally |also |mostly )?(m\. or nt|nt\. or m|m\. and nt|adj|m|f|nt|indecl|ind)\.")
_ROOT = re.compile(r"^\S+ (?:\d\. )?(?:\([^)]*\) )?(?:\d+ )?(?:cl\. ?\d|\(cl\.|[PĀA]\. |Ā\.|P\.)")
_GENDER = {"m": "masc", "f": "fem", "n": "nt", "nt": "nt", "mfn": "adj", "mf(ā)n": "adj", "mf(ī)n": "adj", "adj": "adj", "ind": "ind", "ind.p": "ind", "indecl": "ind",
           "m. n": "masc nt", "m. f": "masc fem", "f. n": "fem nt", "m. or nt": "masc nt", "nt. or m": "masc nt", "m. and nt": "masc nt"}


class Cologne:
    """Read access to ``sanskrit.sqlite``."""

    ORDER = {"bhs": 0, "mw": 1, "ap90": 2}

    def __init__(self, path: Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"sanskrit.sqlite not found at {path} — run `kavi setup --sanskrit`")
        self.con = sqlite3.connect(f"file:{path}?immutable=1", uri=True)
        self.con.row_factory = sqlite3.Row
        self._cache: dict[str, list[sqlite3.Row]] = {}

    def lookup(self, iast: str) -> list[sqlite3.Row]:
        """Every entry whose headword is ``iast`` (a stem or a root): the common word before the proper name (``2 dharma``
        before ``1 Dharma``: Edgerton capitalises a name's headword, Monier-Williams says ``N. of``), Edgerton before
        Monier-Williams before Apte. A nasal is looked up both ways (``saṅgati``, ``saṃgati``, ``sambodhi``)."""
        if iast not in self._cache:
            rows = self.con.execute("SELECT * FROM entries WHERE iast = ?", (iast,)).fetchall()
            if not rows:
                for alt in nasal_variants(iast):
                    rows = self.con.execute("SELECT * FROM entries WHERE iast = ?", (alt,)).fetchall()
                    if rows:
                        break
            rows.sort(key=lambda r: (2 if r["body"].startswith("?") else (1 if self.is_name_body(r["body"]) else 0),
                                     self.ORDER.get(r["source"], 9), int(r["L"]) if str(r["L"]).isdigit() else 0))
            self._cache[iast] = rows
        return self._cache[iast]

    def has_name(self, iast: str) -> bool:
        """Some entry for the headword is a proper name (Subhūti the disciple beside subhūti "well-being")."""
        return any(self.is_name_body(r["body"]) for r in self.lookup(iast))

    @staticmethod
    def is_name_body(body: str) -> bool:
        """Edgerton capitalises the headword of a proper name (``Śāriputra, n. of …``); Monier-Williams says ``N. of``."""
        b = re.sub(r"^\d+ ", "", body or "")
        # "su-bhūti m. N. of a Brāhman"; "a-nātha—piṇḍa-da …, m. ‘giver of food to the poor’, N. of a merchant": the name
        # is the entry's first sense (before its first semicolon); "dharma m. …; N. of …" is a word with a name sense
        return (bool(re.match(r"[A-ZĀĪŪṚṢŚ]", b)) or bool(re.match(r"^\S+ (?:\(\S*\) )?(?:\d\. )?(?:m\. |f\. |n\. )?N\. of", b))
                or bool(re.match(r"^[^;]{0,120}?\bN\. of", b))
                or bool(re.match(r"^of (?:a |an |the )?[A-ZĀĪŪṚṢŚ]", b))
                or bool(re.search(r"\bn\. of a (?:well-known )?Bodhisattva\b", b)))

    def is_name(self, iast: str) -> bool:
        """The dictionaries know the headword only as a proper name (Subhūti, Anāthapiṇḍada)."""
        rows = [r for r in self.lookup(iast) if r["source"] != "ap90"]
        return bool(rows) and all(self.is_name_body(r["body"]) for r in rows)

    def genders(self, iast: str) -> set[str]:
        """The genders (or ``adj``/``ind``) the dictionaries give the headword: Edgerton's where he gives any (with
        Monier-Williams' ``adj`` beside them: parama is an adjective as well as his "high number"), else
        Monier-Williams' (``lakṣaṇa n.`` and ``mfn.``, ``caryā f.``), as ``{"masc", "nt", "adj"}``; a word the
        dictionaries know only as a name (Subhūti) has the name's gender."""
        rows = self.lookup(iast)
        mw: set[str] = set()
        for r in rows:
            if r["source"] == "mw" and not self.is_name_body(r["body"]):       # "rūpa m. N. of a place" is not the word's gender
                m = _GENDER_MW.match(r["body"])
                if m:
                    mw.update(_g(m.group(1)).split())
        bhs = [r for r in rows if r["source"] == "bhs" and not self.is_name_body(r["body"])]
        if bhs:                                                     # Edgerton's first (primary) entry only
            m = _GENDER_BHS.match(bhs[0]["body"])
            if m:
                if m.group(1) == "f" and bhs[0]["body"][m.end():].lstrip().startswith("˚"):
                    return {"masc"} | (mw & {"adj"})                 # "anāgāmin, f. ˚nī": the feminine form of a masculine headword
                return set(_g(m.group(1)).split()) | (mw & {"adj"})
        if not mw and not bhs:
            return self.name_genders(iast)
        return mw

    def gender_counts(self, iast: str) -> dict[str, int]:
        """How much of Monier-Williams' entry (in characters) stands under each gender (``pariṣad``: a line of
        ``mfn.``, several of ``f.``): the commoner use of a word that is both adjective and noun."""
        counts: dict[str, int] = {}
        current: list[str] = []
        for r in self.lookup(iast):
            if r["source"] != "mw":
                continue
            m = _GENDER_MW.match(r["body"])
            if m:
                current = [] if self.is_name_body(r["body"]) else _g(m.group(1)).split()
            for g in current:                                   # the sense lines that follow a gender belong to it
                counts[g] = counts.get(g, 0) + len(r["body"])
        return counts

    def name_genders(self, iast: str) -> set[str]:
        """The genders of the headword's proper-name entries (Subhūti the disciple is masculine)."""
        found: set[str] = set()
        for r in self.lookup(iast):
            if self.is_name_body(r["body"]):
                m = _GENDER_MW.match(r["body"]) if r["source"] == "mw" else _GENDER_BHS.match(r["body"])
                if m:
                    found.update(g for g in _g(m.group(1)).split() if g in ("masc", "fem", "nt"))
        return found

    def is_root(self, iast: str) -> bool:
        """A headword that is only a verbal root (``subh cl. 9. 6. P. subhnāti``), not a nominal stem."""
        rows = self.lookup(iast)
        if not rows:
            return False
        nominal = any(r["source"] == "bhs" and not _ROOT.match(r["body"]) or _GENDER_MW.match(r["body"]) for r in rows)
        return not nominal and any(_ROOT.match(r["body"]) for r in rows)

    def is_letter(self, iast: str) -> bool:
        """A headword that is a letter of the alphabet (``cha the 7th consonant``), not a word."""
        rows = self.lookup(iast)
        return bool(rows) and any(_LETTER.search(r["body"]) for r in rows) and not any(_GENDER_MW.match(r["body"]) for r in rows)

    def weight(self, iast: str) -> int:
        """How much the dictionaries have to say about a headword: a proxy for how common the word is."""
        rows = self.lookup(iast)
        if not rows:
            return 0
        n = {"bhs": 0, "mw": 0, "ap90": 0}
        for r in rows:
            n[r["source"]] = n.get(r["source"], 0) + 1
        return (4 if n["bhs"] else 0) + min(n["mw"], 20) + (1 if n["ap90"] else 0)

    def known(self, iast: str) -> bool:
        return bool(self.lookup(iast))

    def meaning(self, iast: str, limit: int = 300) -> str:
        """A short gloss: the first entry's text, cut at a sentence or clause end."""
        rows = self.lookup(iast)
        if not rows:
            return ""
        text = rows[0]["body"]
        if len(text) > limit:
            cut = text[:limit]
            for sep in (". ", "; "):
                i = cut.rfind(sep)
                if i > limit // 2:
                    cut = cut[: i + 1]
                    break
            text = cut.rstrip() + " …"
        return text
