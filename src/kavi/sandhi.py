"""Reverse sandhi after Kaccāyana's Sandhikappa.

The DPD deconstructor knows 861,706 joined forms; this module handles the rest. Given a word the DPD
cannot gloss, it proposes the pairs (or triples) of words whose junction Kaccāyana's rules would turn
into that form, and keeps the proposals whose parts the DPD does know. The rules it undoes:

* §12 ``Sarā sare lopaṃ`` — a vowel is elided before a vowel; §13 ``Vā paro asarūpā`` — or the following
  dissimilar vowel is; §15/§16 ``Dīghaṃ``, ``Pubbo ca`` — the survivor may be lengthened;
* §14 ``Kvacāsavaṇṇaṃ lutte`` — after elision the next vowel may change class (a + i → e, a + u → o);
* §17 ``Yamedantassādeso``, §18 ``Vamodudantānaṃ``, §21 ``Ivaṇṇo yaṃ navā`` — final e/i → y, o/u → v before
  a vowel; §28 ``Para dvebhāvo ṭhāne`` — the following consonant may double;
* §19 ``Sabbo caṃ ti``, §47 ``Atissa canatassa`` — ti/ati + vowel → cc (paccuttaritvā, accantaṃ);
  §44 ``Abbho abhi``, §45 ``Ajjho adhi`` — abhi/adhi + vowel → abbh/ajjh;
* §31 ``Vaggantaṃ vā vagge`` — a niggahīta becomes the class nasal before a consonant of its class;
  §34 ``Madā sare`` — m or d before a vowel; §35 ``Ya va ma da na ta ra lā cāgamā`` — an augment consonant
  is inserted between vowels; §38/§40 — the niggahīta or the following vowel is elided (kiṃ + iti → kinti);
* the quoting ``iti`` glued to the preceding word (hotīti, evanti), and the plain juxtaposition of a
  compound's members (buddha + vacanaṃ), with the doubling of §28 undone.

Proposals are scored: two parts beat three; parts the texts use often (the DPD's frequency count) beat
rare homonyms; the quoting ``iti`` and the common prefixes get the benefit of the doubt; a part shorter
than three letters must be a known particle or prefix.
"""

from __future__ import annotations

import math
from typing import Callable

VOWELS = "aāiīuūeo"
SHORTEN = {"ā": "a", "ī": "i", "ū": "u"}
AGAMA = set("yvmdntrlḷ")
CONSONANT_CLASSES = {"ṅ": "kg", "ñ": "cj", "ṇ": "ṭḍ", "n": "td", "m": "pb"}
PREFIX_UNDO = {"abbh": "abhi", "ajjh": "adhi", "pacc": "pati", "acc": "ati"}
PARTICLES = {"a", "na", "ca", "vā", "hi", "ce", "te", "me", "so", "sā", "no", "tu", "pi", "va", "ye", "ya", "yo", "yā",
             "kho", "ko", "kā", "su", "u", "ā", "i", "ma", "mā", "sa", "vi", "ni", "pa", "du", "o", "ud", "nī", "he", "re",
             "bho", "ke", "ki", "ku", "se", "si", "sū"}
PREFIXES = {"a", "an", "su", "du", "vi", "ni", "pa", "saṃ", "adhi", "ati", "abhi", "anu", "apa", "api", "upa", "pari",
            "pati", "paṭi", "ud", "o", "ava", "nī", "ā", "ppa", "pā"}
QUOTATIVE = {"iti", "ti"}

Freq = Callable[[str], float]


def _cands(w: str) -> list[tuple[str, str, str]]:
    """Unvalidated (left, right, rule) proposals for a two-way split."""
    out: list[tuple[str, str, str]] = []
    n = len(w)

    def add(left: str, right: str, rule: str, vowel_rule: bool = False):
        if not left or not right or left == w or right == w:
            return
        out.append((left, right, rule))
        if len(right) > 2 and right[0] == right[1] and right[0] not in VOWELS:
            out.append((left, right[1:], rule + "+§28"))          # doubling of the following consonant undone
        if vowel_rule and right[0] in SHORTEN:
            out.append((left, SHORTEN[right[0]] + right[1:], rule + "+§15"))   # lengthened survivor (right)
        if vowel_rule and left[-1] in SHORTEN:
            out.append((left[:-1] + SHORTEN[left[-1]], right, rule + "+§16"))   # lengthened survivor (left)

    for pref, full in PREFIX_UNDO.items():
        if w.startswith(pref) and n > len(pref) + 1 and w[len(pref)] in VOWELS:
            add(full, w[len(pref):], "prefix", vowel_rule=True)

    for i in range(1, n):
        c, prev = w[i], w[i - 1]
        if 2 <= i <= n - 2:
            add(w[:i], w[i:], "juxtaposition")
        if c in VOWELS and prev not in VOWELS:
            for v in VOWELS:
                add(w[:i] + v, w[i:], "§12", vowel_rule=True)          # left final elided
            for v in VOWELS:
                add(w[:i + 1], v + w[i + 1:], "§13", vowel_rule=True)  # right initial elided
            if c == "e":
                add(w[:i] + "a", "i" + w[i + 1:], "§14")
                add(w[:i] + "a", "ī" + w[i + 1:], "§14")
            if c == "o":
                add(w[:i] + "a", "u" + w[i + 1:], "§14")
                add(w[:i] + "a", "ū" + w[i + 1:], "§14")
        if i + 1 < n and w[i + 1] in VOWELS and prev not in VOWELS:
            if c == "y":
                add(w[:i] + "e", w[i + 1:], "§17", vowel_rule=True)
                add(w[:i] + "i", w[i + 1:], "§21", vowel_rule=True)
            if c == "v":
                add(w[:i] + "o", w[i + 1:], "§18", vowel_rule=True)
                add(w[:i] + "u", w[i + 1:], "§18", vowel_rule=True)
        if i + 1 < n and prev in VOWELS and w[i + 1] in VOWELS:
            if c in AGAMA:
                add(w[:i], w[i + 1:], "§35")
            if c in "md":
                add(w[:i] + "ṃ", w[i + 1:], "§34")
        if i + 1 < n and c in CONSONANT_CLASSES and w[i + 1] in CONSONANT_CLASSES[c] + "ṃ" and prev in VOWELS:
            add(w[:i] + "ṃ", w[i + 1:], "§31")
        if c == "c" and i + 2 < n and w[i + 1] == "c" and w[i + 2] in VOWELS and prev in VOWELS:
            add(w[:i] + "ti", w[i + 2:], "§19")
    # the quoting iti: -eti/-āti/-īti/-ūti/-oti ← vowel + iti; -nti ← -ṃ + iti (§40 + §31)
    for end, heads in (("eti", "aāe"), ("īti", "iī"), ("ūti", "uū"), ("āti", "aā"), ("oti", "o")):
        if w.endswith(end) and n > len(end) + 1:
            for h in heads:
                out.append((w[: -len(end)] + h, "iti", "iti"))
    if w.endswith("nti") and n > 4:
        out.append((w[:-3] + "ṃ", "iti", "iti"))
    return out


def part_ok(part: str, known: Callable[[str], bool]) -> bool:
    if len(part) <= 2:
        return part in PARTICLES or part in PREFIXES or part in QUOTATIVE
    return known(part)


def part_weight(part: str, freq: Freq | None) -> float:
    if part in QUOTATIVE:
        return 3.0 if part == "iti" else 2.0
    if part in PREFIXES:
        return 1.5
    f = freq(part) if freq else 0.0
    return math.log1p(f) / 3.0 if f > 0 else (0.0 if len(part) > 2 else -0.5)


def score_parts(parts: list[str], rule: str, freq: Freq | None) -> float:
    """Two parts beat three; frequent parts beat rare homonyms; a vowel change costs a little."""
    s = 10.0 - 3 * (len(parts) - 2)
    s += sum(part_weight(p, freq) for p in parts) / len(parts)
    if "+§" in rule:
        s -= 0.3
    if rule == "juxtaposition":
        s += 0.2
    return s


def rank_splits(candidates: list[list[str]], known: Callable[[str], bool], freq: Freq | None = None,
                curated: set[str] | None = None) -> list[list[str]]:
    """Order splits from any source (the DPD deconstructor, these heuristics): complete ones first, then by score;
    a split the DPD itself gives (``curated``) is trusted over a heuristic one of the same completeness."""
    scored = []
    for i, parts in enumerate(candidates):
        complete = all(part_ok(p, known) for p in parts)
        is_curated = 1 if curated and " + ".join(parts) in curated else 0
        scored.append(((1 if complete else 0), is_curated, score_parts(parts, "external", freq), -i, parts))
    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3]), reverse=True)
    out, seen = [], set()
    for _, _, _, _, parts in scored:
        key = " + ".join(parts)
        if key not in seen:
            seen.add(key)
            out.append(parts)
    return out


def lengthened_variant(word: str, known: Callable[[str], bool]) -> str | None:
    """khāyatī (before a following ti, §15) -> khāyati: a final long vowel shortened, if that is a known word."""
    if word and word[-1] in SHORTEN:
        short = word[:-1] + SHORTEN[word[-1]]
        if known(short):
            return short
    return None


def split(word: str, known: Callable[[str], bool], freq: Freq | None = None, max_parts: int = 3,
          limit: int = 4) -> list[list[str]]:
    """Validated splits of ``word`` into parts the DPD knows, best first."""
    word = word.lower()
    if len(word) < 4:
        return []
    results: dict[str, tuple[float, list[str]]] = {}

    def ok(part: str) -> bool:
        return part_ok(part, known)

    def score(parts: list[str], rule: str) -> float:
        return score_parts(parts, rule, freq)

    for left, right, rule in _cands(word):
        if not ok(left):
            continue
        if ok(right):
            key = " + ".join((left, right))
            cand = (score([left, right], rule), [left, right])
            if key not in results or cand[0] > results[key][0]:
                results[key] = cand
        elif max_parts > 2 and len(right) >= 4:
            for tail in split(right, known, freq, max_parts - 1, limit=2):
                parts = [left] + tail
                key = " + ".join(parts)
                cand = (score(parts, rule), parts)
                if key not in results or cand[0] > results[key][0]:
                    results[key] = cand
    ranked = sorted(results.values(), key=lambda t: -t[0])
    return [parts for _, parts in ranked[:limit]]
