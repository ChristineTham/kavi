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
from .language import LANGUAGE

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

HONORIFICS = {
    "bhagavat", "bhagavant", "bhagavān", "bhagavan", "āyuṣmat", "āyuṣmant", "āyuṣman", "bhadanta", "bhadra", "bho", "bhavat", "bhavant",
    "tathāgata", "arhat", "arhant", "samyaksaṃbuddha", "samyaksambuddha", "buddha", "sugata", "jina", "śāstṛ", "śāstar",
    "bhikṣu", "bhikṣuṇī", "śrāmaṇera", "upāsaka", "upāsikā", "śramaṇa", "brāhmaṇa", "parivrājaka", "bodhisattva", "mahāsattva",
    "śrāvaka", "mahāśrāvaka", "deva", "mahārāja", "ācārya", "upādhyāya", "sthavira", "mahāsthavira", "ārya",
    "lokanāyaka", "lokanātha", "nāyaka", "nātha", "mahānubhāva", "kulaputra",
    "lokavid", "puruṣadamyasārathi", "vidyācaraṇasampanna",
    # Pāli
    "bhagavā", "āyasmā", "bhante", "āvuso", "bhikkhu", "satthā", "satthar", "kulaputta"
}

HONORIFIC_MEANINGS: dict[str, str] = {
    "bhagavat": "the Blessed One", "bhagavant": "the Blessed One", "bhagavān": "the Blessed One", "bhagavan": "the Blessed One", "bhagavā": "the Blessed One",
    "āyuṣmat": "venerable", "āyuṣmān": "venerable", "āyuṣman": "venerable", "āyasmā": "venerable",
    "bhadanta": "venerable sir", "bhante": "venerable sir", "āvuso": "friend",
    "bhikṣu": "monks", "bhikṣavaḥ": "monks", "bhikkhu": "monks", "kulaputra": "noble sons", "kulaputrāḥ": "noble sons", "kulaputta": "noble sons",
    "mahārāja": "great king", "deva": "your majesty",
    "sugata": "well-gone one", "tathāgata": "thus-gone one", "śāstṛ": "teacher", "śāstar": "teacher", "satthā": "teacher",
    "jina": "conqueror", "arhat": "worthy one", "buddha": "the Awakened One",
    "samyaksaṃbuddha": "perfectly awakened one", "samyaksambuddha": "perfectly awakened one",
    "bodhisattva": "awakening-being", "mahāsattva": "great being",
    "lokanāyaka": "guide of the world", "lokanātha": "protector of the world", "nāyaka": "guide", "nātha": "protector",
    "lokavid": "knower of the world", "puruṣadamyasārathi": "unsurpassed guide of persons to be tamed",
    "vidyācaraṇasampanna": "endowed with knowledge and conduct",
    "mahānubhāva": "of great might",
    "śrāvaka": "disciple", "mahāśrāvaka": "great disciple",
}

HONORIFIC_VARIANTS: dict[str, list[str]] = {
    "bhagavat": ["the Blessed One", "the Blessed Ones", "Blessed One", "Blessed Ones", "the Lord", "Lord", "the Exalted One", "Exalted One", "the Fortunate One", "Fortunate One"],
    "bhagavant": ["the Blessed One", "the Blessed Ones", "Blessed One", "Blessed Ones", "the Lord", "Lord", "the Exalted One", "Exalted One", "the Fortunate One", "Fortunate One"],
    "bhagavān": ["the Blessed One", "the Blessed Ones", "Blessed One", "Blessed Ones", "the Lord", "Lord", "the Exalted One", "Exalted One", "the Fortunate One", "Fortunate One"],
    "bhagavan": ["the Blessed One", "the Blessed Ones", "Blessed One", "Blessed Ones", "the Lord", "Lord", "the Exalted One", "Exalted One", "the Fortunate One", "Fortunate One"],
    "bhagavā": ["the Blessed One", "the Blessed Ones", "Blessed One", "Blessed Ones", "the Lord", "Lord", "the Exalted One", "Exalted One", "the Fortunate One", "Fortunate One"],
    "āyuṣmat": ["the venerable one", "the venerable ones", "venerable one", "venerable ones", "the venerable", "venerable", "the reverend", "reverend", "the elder", "elder"],
    "āyuṣmān": ["the venerable one", "the venerable ones", "venerable one", "venerable ones", "the venerable", "venerable", "the reverend", "reverend", "the elder", "elder"],
    "āyuṣman": ["the venerable one", "the venerable ones", "venerable one", "venerable ones", "the venerable", "venerable", "the reverend", "reverend", "the elder", "elder"],
    "āyasmā": ["the venerable one", "the venerable ones", "venerable one", "venerable ones", "the venerable", "venerable", "the reverend", "reverend", "the elder", "elder"],
    "bhadanta": ["venerable sir", "venerable lord", "venerable one", "venerable", "reverend sir", "reverend"],
    "bhante": ["venerable sir", "reverend sir", "lord", "sir"],
    "āvuso": ["friends", "friend", "brothers", "brother"],
    "bhikṣu": ["monks", "monk", "mendicants", "mendicant"],
    "bhikṣavaḥ": ["monks", "monk", "mendicants", "mendicant"],
    "bhikkhu": ["monks", "monk", "mendicants", "mendicant"],
    "kulaputra": ["noble sons", "noble son", "sons of good family", "son of good family", "gentlemen", "gentleman", "good sons", "good son"],
    "kulaputrāḥ": ["noble sons", "noble son", "sons of good family", "son of good family", "gentlemen", "gentleman", "good sons", "good son"],
    "kulaputta": ["noble sons", "noble son", "sons of good family", "son of good family"],
    "mahārāja": ["O great king", "great king", "your majesty", "sire"],
    "sugata": ["the Well-Gone One", "the Well-gone One", "Well-Gone One", "Well-gone One", "well-gone one", "the well-gone one"],
    "śāstṛ": ["the Teacher", "the teacher", "Teacher", "teacher"],
    "śāstar": ["the Teacher", "the teacher", "Teacher", "teacher"],
    "satthā": ["the Teacher", "the teacher", "Teacher", "teacher"],
    "jina": ["the Conqueror", "the conqueror", "Conqueror", "conqueror", "the Victor", "the victor", "Victor", "victor"],
    "tathāgata": [
        "the Thus-Gone One", "the Thus-Gone Ones", "the Thus-gone One", "the Thus-gone Ones",
        "Thus-Gone One", "Thus-Gone Ones", "Thus-gone One", "Thus-gone Ones", "Thus-gone ones",
        "thus-gone one", "thus-gone ones", "the thus-gone one", "the thus-gone ones",
        "thus-come one", "thus-come ones", "the thus-come one", "the thus-come ones",
    ],
    "arhat": [
        "the Worthy One", "the Worthy Ones", "the Worthy ones", "Worthy One", "Worthy Ones", "Worthy ones",
        "worthy one", "worthy ones", "the worthy one", "the worthy ones",
        "the liberated one", "the liberated ones", "liberated one", "liberated ones",
        "the saint", "the saints", "saint", "saints",
    ],
    "samyaksaṃbuddha": [
        "the Perfectly Awakened One", "the Perfectly Awakened Ones", "the Perfectly Awakened ones",
        "Perfectly Awakened One", "Perfectly Awakened Ones", "Perfectly Awakened ones",
        "perfectly awakened one", "perfectly awakened ones", "the perfectly awakened one", "the perfectly awakened ones",
        "the Perfectly Enlightened One", "the Perfectly Enlightened Ones", "the Perfectly Enlightened ones",
        "Perfectly Enlightened One", "Perfectly Enlightened Ones", "Perfectly Enlightened ones",
        "perfectly enlightened one", "perfectly enlightened ones", "the perfectly enlightened one", "the perfectly enlightened ones",
        "fully enlightened one", "fully enlightened ones", "the fully enlightened one", "the fully enlightened ones",
        "fully awakened one", "fully awakened ones", "the fully awakened one", "the fully awakened ones",
    ],
    "samyaksambuddha": [
        "the Perfectly Awakened One", "the Perfectly Awakened Ones", "the Perfectly Awakened ones",
        "Perfectly Awakened One", "Perfectly Awakened Ones", "Perfectly Awakened ones",
        "perfectly awakened one", "perfectly awakened ones", "the perfectly awakened one", "the perfectly awakened ones",
        "the Perfectly Enlightened One", "the Perfectly Enlightened Ones", "the Perfectly Enlightened ones",
        "Perfectly Enlightened One", "Perfectly Enlightened Ones", "Perfectly Enlightened ones",
        "perfectly enlightened one", "perfectly enlightened ones", "the perfectly enlightened one", "the perfectly enlightened ones",
        "fully enlightened one", "fully enlightened ones", "the fully enlightened one", "the fully enlightened ones",
        "fully awakened one", "fully awakened ones", "the fully awakened one", "the fully awakened ones",
    ],
    "bodhisattva": [
        "the Bodhisattva", "the Bodhisattvas", "Bodhisattva", "Bodhisattvas",
        "the bodhisattva", "the bodhisattvas", "bodhisattva", "bodhisattvas",
        "awakening beings", "awakening being", "the awakening being", "the awakening beings",
        "awakened beings", "awakened being",
    ],
    "mahāsattva": [
        "the Mahāsattva", "the Mahāsattvas", "Mahāsattva", "Mahāsattvas",
        "the mahāsattva", "the mahāsattvas", "mahāsattva", "mahāsattvas",
        "great beings", "great being", "the great being", "the great beings",
    ],
    "lokanāyaka": [
        "leader of the worlds", "leader of the world", "guide of the worlds", "guide of the world",
        "the leader of the worlds", "the leader of the world", "the guide of the worlds", "the guide of the world",
        "Leader of the World", "Guide of the World",
    ],
    "lokanātha": [
        "protector of the worlds", "protector of the world", "lord of the worlds", "lord of the world",
        "the protector of the worlds", "the protector of the world", "the lord of the worlds", "the lord of the world",
        "Protector of the World", "Lord of the World",
    ],
    "nāyaka": ["the guide", "guide", "the leader", "leader"],
    "nātha": ["the protector", "protector", "the lord", "lord"],
    "mahānubhāva": ["of great might", "mighty one", "O mighty one", "the mighty one", "one of great might"],
    "śrāvaka": ["disciples", "disciple", "hearers", "hearer"],
    "mahāśrāvaka": ["great disciples", "great disciple"],
    "buddha": [
        "the awakened one", "the awakened ones", "the Awakened One", "the Awakened Ones",
        "the enlightened one", "the enlightened ones", "the Enlightened One", "the Enlightened Ones",
        "awakened one", "awakened ones", "enlightened one", "enlightened ones",
    ],
    "lokavid": [
        "the knower of the world", "the knower of the worlds", "knower of the world", "knower of the worlds",
        "the knower of worlds", "knower of worlds",
    ],
    "puruṣadamyasārathi": [
        "unsurpassed charioteer of men to be tamed", "unsurpassed charioteer of persons to be tamed", "unsurpassed charioteer of beings to be tamed",
        "the unsurpassed charioteer of men to be tamed", "the unsurpassed charioteer of persons to be tamed", "the unsurpassed charioteer of beings to be tamed",
        "unsurpassed guide of men to be tamed", "unsurpassed guide of persons to be tamed",
        "the unsurpassed guide of men to be tamed", "the unsurpassed guide of persons to be tamed",
        "charioteer of men to be tamed", "charioteer of persons to be tamed",
        "the charioteer of men to be tamed", "the charioteer of persons to be tamed",
    ],
    "vidyācaraṇasampanna": [
        "endowed with knowledge and conduct", "perfect in knowledge and conduct",
        "possessed of knowledge and conduct", "accomplished in knowledge and conduct",
        "endowed with wisdom and conduct", "perfect in wisdom and conduct",
    ],
}

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


def _clean_dict_gloss(raw: str) -> str:
    """Clean raw Monier-Williams / Cologne dictionary prefixes and citations from a headword meaning."""
    s = re.sub(r"^[^:;]{1,30}:\s*", "", (raw or "").split(";")[0]).strip()
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\b(?:mf\([^)]*\)n|mfn|m|f|n|ind|cl\.\s*\d+\.?|P\.|Ā\.|See\s+p\.\s*\d+[^,.;]*)\b\.?\s*", "", s)
    s = re.sub(r"\s*\([^)]*(?:RV|AV|MBh|Kāv|Pāṇ|cf\.|lit\.|See|s\.v|&c\.)[^)]*\)", "", s)
    s = re.sub(r",\s*(?:Buddh|Jain|Ved|RV|AV|MBh|Kāv)\.?.*$", "", s)
    s = re.sub(r"\s*'\s*'\s*$", "", s).strip(" ,.;:-—")
    return s


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


TERM_SPAN_RE = re.compile(r"`([^`]+)` \(([^()]*)\)")


def term_key(term: str) -> str:
    """The key under which a `term` (gloss) span counts as one term across its inflected forms."""
    return re.sub(r"[ṃṁḥoāaeīiūs]+$", "", term.lower())


def _protected(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in TERM_SPAN_RE.finditer(text)]


def _inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def lint(analyses: list[Analysis], translation: str, glossary: dict[str, str] | None = None,
         apply: bool = True, alternatives: dict[str, list[str]] | None = None,
         glossed: set[str] | None = None) -> tuple[str, list[Finding]]:
    """Check ``translation`` against the word analyses; return (possibly amended translation, findings)."""
    text = translation
    findings: list[Finding] = []
    seen: set[str] = set()
    glossary = glossary or {}
    alternatives = alternatives or {}
    if glossed is None:
        glossed = set()
    is_sa = LANGUAGE.get("code") == "sa"
    if apply:
        text = re.sub(r"\bThus (?:have I|I have|it was|was) heard(?:\s+by me)?\b", "Thus heard by me", text, flags=re.I)
    if is_sa and apply:
        text = re.sub(r"^yaduta\b", "Namely", text, flags=re.I)
        text = re.sub(r"\byaduta\b", "namely", text, flags=re.I)

    # glossary terms inside compounds (nāmarūpanirodho) also fix the rendering of the term wherever it appears: the
    # term must be a word or a compound member of the sentence, not a substring of one (bhava is not in bhavet, whose
    # alternative "being" would otherwise turn every "being" of the sentence into "existence")
    present: set[str] = set()
    for a in analyses:
        for h in a.headwords[:1]:
            present.add(h.stem)
            present.update(m for m in (h.compound_construction or "").split(" + ") if m)
            present.update(m.strip() for m in (h.construction or "").split(" + ") if m.strip())
    for stem, gloss in glossary.items():
        if is_sa and stem in HONORIFICS:
            continue
        if gloss and stem in present:
            others = [v for v in alternatives.get(stem, []) if v.lower() != gloss.lower()]
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

        is_real_name = bool(h and h.kind == "name")
        base_kind = h.kind if (h and h.kind != "name") else ""
        if is_sa:
            h_parses = [h.parses] if isinstance(h.parses, str) else (h.parses if h else [])
            a_parses = [a.parses] if isinstance(getattr(a, "parses", None), str) else (getattr(a, "parses", []) or [])
            is_voc = (h is None or (h.pos != "ind" and h.kind != "name")) and (
                (bool(h_parses) and all("voc" in p for p in h_parses)) or (bool(a_parses) and all("voc" in p for p in a_parses))
            )
            is_hon = (h and h.kind != "name" and (h.kind == "honorific" or h.stem.lower() in HONORIFICS or h.stem.lower() in HONORIFIC_MEANINGS)) or is_voc
            kind = "name" if is_real_name else ("honorific" if is_hon else ("technical" if gstem in glossary else base_kind))
        else:
            kind = "technical" if gstem in glossary else ("name" if is_real_name else base_kind)

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
            o_pat = re.compile(r"\b(?:O|Oh),?\s+(" + re.escape(stem) + r")\b", re.I)
            text = o_pat.sub(r"\1", text)
        elif kind == "honorific":
            if not is_sa:
                form = honorific_form(h.stem, surface, h.parses, getattr(h, "family_set", ""))
                hit = _replace_english(text, _plural_variants(english_variants(h, a.headwords)), form, apply, every=True, keep_article=True)
                if hit:
                    text, phrase = hit
                    findings.append(Finding(surface, f"an honorific rendered in English as '{phrase}'",
                                            f"replaced by '{form}'" if apply else f"replace by '{form}'", "fix" if apply else "ask"))
                elif not (_present(form, text) or _present(h.stem[:5], text)):
                    findings.append(Finding(surface, f"an honorific ({h.meaning.split(';')[0]}) does not appear untranslated",
                                            f"put '{form}' in place of whatever English stands for it"))
            else:
                form = honorific_form(h.stem, surface, h.parses, getattr(h, "family_set", ""))
                if is_voc:
                    form = surface
                if form.lower() in ("bhagavan", "bhadanta", "ayusman", "āyuṣman"):
                    form = form.capitalize()
                key = (h.stem if h else surface).lower()
                known = HONORIFIC_VARIANTS.get(key, []) + HONORIFIC_VARIANTS.get(surface.lower(), [])
                phrases = known + [f"O {p}" for p in known] + [f"O, {p}" for p in known] + [f"Oh {p}" for p in known]
                if h:
                    d_vars = _plural_variants(english_variants(h, a.headwords))
                    phrases += d_vars + [f"O {v}" for v in d_vars] + [f"O, {v}" for v in d_vars]
                if is_voc:
                    phrases += [f"O {form}", f"O, {form}", f"Oh {form}", f"O {surface}", f"O, {surface}", f"Oh {surface}"]
                phrases = sorted(set(phrases), key=len, reverse=True)

                hit = _replace_english(text, phrases, form, apply, every=True, keep_article=True, plural_aware=True)
                if hit:
                    text, phrase = hit
                    findings.append(Finding(surface, f"honorific/vocative rendered in English as '{phrase}'",
                                            f"replaced by '{form}'" if apply else f"replace by '{form}'", "fix" if apply else "ask"))
                elif not (_present(form, text) or _present(key[:5], text)):
                    findings.append(Finding(surface, f"honorific/vocative does not appear untranslated",
                                            f"put '{form}' in place of whatever English stands for it"))
                o_pat = re.compile(r"\b(?:O|Oh),?\s+(" + re.escape(form) + r")\b", re.I)
                text = o_pat.sub(r"\1", text)
        elif kind == "technical":
            gloss = glossary.get(gstem) or _clean_dict_gloss(h.meaning or h.meaning_2)
            if gstem in ("sūtra", "sutra") or gloss.lower() in ("sūtra", "sutra"):
                gloss = "discourse"
            elif gstem == "bodhisattva" or gloss.lower() == "bodhisattva":
                gloss = "awakening-being"
            elif gstem == "mahāsattva" or gloss.lower() == "mahāsattva":
                gloss = "great being"
            elif gstem == "buddha" or gloss.lower() == "buddha":
                gloss = "the Awakened One"
            elif gstem == "tathatā":
                gloss = "suchness"
            elif gstem not in glossary and gloss and (
                len(gloss) > 35 or any(x in gloss for x in ("(", ")", "[", "]", "〔", "〕", "=", "fr.", "q.v", "ib", "Skt", "Pali")) or re.search(r"\d", gloss)
            ):
                gloss = ""
            form = term_form(gstem, surface, h.parses)
            if not is_sa:
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
                        if m.group(0)[0].isupper() and not shown[0].isupper():
                            shown = shown[0].upper() + shown[1:]
                        text = text[: m.start()] + f"`{shown}` ({gloss})" + text[m.end():]
                    glossed.add(gstem)
                    findings.append(Finding(surface, "technical term left bare", f"written as `{form}` ({gloss})" if apply else f"write `{form}` ({gloss})",
                                            "fix" if apply else "ask"))
                elif gstem in glossary:
                    findings.append(Finding(surface, f"technical term ({gloss}) not shown in the `word` (gloss) form",
                                            f"write it as `{form}` ({gloss}) on its first occurrence, then '{gloss}'"))
            else:
                # Sanskrit technical terms: untranslated on subsequent encounters, `word` (gloss) on first encounter
                raw_vars = _plural_variants(([gloss] if gloss else []) + (alternatives.get(gstem, []) if alternatives else []) + english_variants(h))
                skip_forms = {form.lower(), gstem.lower(), surface.lower(), form.lower() + "s", gstem.lower() + "s"}
                variants = [v for v in raw_vars if v.lower() not in skip_forms]
                if gstem not in glossed and gloss:
                    hit = _replace_english(text, variants, f"`{form}` ({gloss})", apply, keep_article=True, plural_aware=True)
                    if hit:
                        text, phrase = hit
                        glossed.add(gstem)
                        findings.append(Finding(surface, f"technical term rendered as plain '{phrase}'",
                                                f"written as `{form}` ({gloss}) on first use" if apply else f"write `{form}` ({gloss}) on first use", "fix" if apply else "ask"))
                    elif re.search(r"`" + re.escape(gstem[:-1]) + r"[^`]*`", text, re.I):
                        glossed.add(gstem)
                    else:
                        bare = re.compile(ARTICLE_RE + r"\b(?:" + re.escape(form) + "|" + re.escape(surface) + r")s?\b", re.I)
                        bm = next((m for m in bare.finditer(text) if not _inside(m.start(), _protected(text))), None)
                        if bm and apply:
                            art = ARTICLE_ONLY_RE.match(bm.group(0))
                            a_str = art.group(1) if art else ""
                            text = text[:bm.start()] + f"{a_str}`{form}` ({gloss})" + text[bm.end():]
                            glossed.add(gstem)
                else:
                    # Subsequent encounters: replace any English variants with bare untranslated form
                    hit = _replace_english(text, variants, form, apply, every=True, keep_article=True, plural_aware=True)
                    if hit:
                        text, phrase = hit
                        findings.append(Finding(surface, f"technical term rendered in English as '{phrase}'",
                                                f"replaced by '{form}'" if apply else f"replace by '{form}'", "fix" if apply else "ask"))
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
    if is_sa and apply:
        text = re.sub(r"\b(?:O|Oh),?\s+(?=[A-ZĀĪŪṚŚṢṆṬḌṄÑa-zāīūṛśṣṇṭḍṅñ`])", "", text)
        text = re.sub(r"\bEnlightened\b", "Awakened", text)
        text = re.sub(r"\benlightened\b", "awakened", text)

        hon_checks = [
            ("bhagavat", "Bhagavān"),
            ("āyuṣmat", "āyuṣmān"),
            ("tathāgata", "Tathāgata"),
            ("arhat", "Arhat"),
            ("samyaksaṃbuddha", "Samyaksaṃbuddha"),
            ("sugata", "Sugata"),
            ("vidyācaraṇasampanna", "vidyācaraṇasaṃpanna"),
            ("lokavid", "lokavid"),
            ("puruṣadamyasārathi", "anuttaraḥ puruṣadamyasārathiḥ"),
            ("śāstṛ", "Śāstṛ"),
            ("buddha", "Buddha"),
            ("jina", "Jina"),
            ("lokanāyaka", "lokanāyaka"),
            ("lokanātha", "lokanātha"),
            ("nāyaka", "nāyaka"),
            ("nātha", "nātha"),
            ("mahānubhāva", "mahānubhāva"),
            ("bhadanta", "Bhadanta"),
            ("kulaputra", "kulaputrāḥ"),
            ("bhikṣu", "bhikṣu"),
            ("mahāśrāvaka", "mahāśrāvaka"),
            ("śrāvaka", "śrāvaka"),
            ("bodhisattva", "bodhisattva"),
            ("mahāsattva", "mahāsattva"),
        ]
        # only the honorifics this unit's source contains (a word or a compound member): "teacher" is not
        # śāstṛ in a sentence about an ācārya
        in_source = present | {h.stem for a in analyses for h in a.headwords[:3]}
        for h_key, h_form in hon_checks:
            phrases = HONORIFIC_VARIANTS.get(h_key, [])
            if not phrases or not any(x == h_key or (x.startswith(h_key[:-1]) and len(x) <= len(h_key) + 2) for x in in_source):
                continue
            hit_rest = _replace_english(text, phrases, h_form, apply=True, every=True, keep_article=True, plural_aware=True)
            if hit_rest:
                text, _ = hit_rest
    return normalise_terms(text), findings


OF_BASE_RE = re.compile(r"\b(?:of|from) ([a-zāīūṃṅñṭḍṇḷ]+)")


def _glossary_stem(h: Headword, glossary: dict[str, str]) -> str:
    """The stem form that this headword matches in the glossary: its own, or the base lemma of an irregular-form entry
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
    term once — later `word` (gloss) occurrences become the plain gloss (Pāli) or the plain word (Sanskrit)."""
    text = re.sub(r"(`([^`]+)` \([^()]*\)) \(\*{0,2}_{0,2}([^()*_]+)_{0,2}\*{0,2}\)",
                  lambda m: m.group(1) if _same_stem(m.group(2), m.group(3)) else m.group(0), text)
    # "dependent origination (*paṭiccasamuppāda*)": English gloss followed by the italic Pāḷi — make it the term form
    text = re.sub(r"\b([A-Za-z][\w -]{2,40}?) \(\*{1,2}([a-zāīūṃṅñṭḍṇḷ]+)\*{1,2}\)", r"`\2` (\1)", text)
    text = re.sub(r"`[^`]+` \((`[^`]+` \([^()]*\))\)", r"\1", text)
    return gloss_once(text, set())


def gloss_once(text: str, seen: set[str]) -> str:
    """The first `word` (gloss) of each term stays; a later one becomes the plain word (Sanskrit) or the plain
    gloss (Pāli). ``seen`` carries the terms already met, across calls."""
    def once(m: re.Match) -> str:
        key = term_key(m.group(1))
        if key in seen:
            return m.group(1) if LANGUAGE.get("code") == "sa" else m.group(2)
        seen.add(key)
        return m.group(0)

    return TERM_SPAN_RE.sub(once, text)


def _fix_tense(text: str, meanings: list[str], apply: bool) -> tuple[str, str, str] | None:
    """'was living' -> 'lives' when a DPD meaning shares the participle's first letters; 'were …' -> plural."""
    for m in re.finditer(r"\b(was|were|is|are)\s+(\w+?)ing\b", text, re.I):
        aux, base = m.group(1).lower(), m.group(2).lower()
        for e in meanings:
            verb = e.split(" ")[0]
            if verb[:3] == base[:3]:
                now = verb if aux in ("was", "is") else (verb[:-1] if verb.endswith("s") else verb)
                if apply:
                    text = text[: m.start()] + now + text[m.end():]
                return text, m.group(0), now
    return None


PREFIX_ONLY_RE = re.compile(r"^((?:(?:O|Oh),?\s+)?(?:(?:the|a|an|this|that|these|those)\s+)?)", re.I)
VOC_STRIP_RE = re.compile(r"^(?:O|Oh),?\s+", re.I)
ARTICLE_ONLY_RE = re.compile(r"^((?:the|a|an|this|that|these|those)\s+)", re.I)


def _replace_english(text: str, phrases: list[str], replacement: str | None, apply: bool, every: bool = False,
                     gloss_for: str | None = None, keep_article: bool = False,
                     plural_aware: bool = False) -> tuple[str, str] | None:
    """Find the first of ``phrases`` in ``text`` (with an optional article or vocative 'O ') and replace it — every
    occurrence for names and honorifics, the first only for a technical term, which becomes `word` (matched phrase)."""
    spans = _protected(text)
    lowered = {p.lower() for p in phrases}
    first: str | None = None
    for phrase in phrases:
        # "name and form" also matches "name-and-form"
        body = r"[\s-]+".join(re.escape(w) for w in phrase.split())
        right = r"\b" if phrase and phrase[-1].isalnum() else ""
        pat = re.compile(ARTICLE_RE + r"\b" + body + right, re.I)
        m = next((mm for mm in pat.finditer(text) if not _inside(mm.start(), spans)), None)
        if m:
            if apply:
                def sub(mm: re.Match) -> str:
                    if _inside(mm.start(), spans):
                        return mm.group(0)                    # never edit inside an existing `term` (gloss)
                    pref_m = PREFIX_ONLY_RE.match(mm.group(0))
                    pref = pref_m.group(1) if pref_m else ""
                    art = VOC_STRIP_RE.sub("", pref)
                    core = mm.group(0)[len(pref):]
                    if gloss_for is not None:
                        gf = gloss_for if (not core or core[0].isupper() or not art.strip()) else (gloss_for[:1].lower() + gloss_for[1:])
                        return f"{art}`{gf}` ({core})"
                    rep = replacement or ""
                    head_w = core.split(" of ")[0].strip().split()[-1].lower() if " of " in core.lower() else core.strip().split()[-1].lower() if core.strip() else ""
                    whole = core.strip().lower()            # "verses" beside "verse" is a plural; "alms" is not
                    is_pl = (head_w.endswith("s") and not head_w.endswith(("ss", "us", "is"))
                             and (whole[:-1] in lowered or whole[:-3] + "y" in lowered or whole not in lowered))
                    if plural_aware and is_pl:
                        m_term = re.match(r"^`([^`]+)` \(([^()]+)\)$", rep)
                        if m_term:
                            t_w, t_m = m_term.group(1), m_term.group(2)
                            if not t_w.lower().endswith(("s", "ḥ", "aḥ", "āḥ")):
                                t_w += "s"
                            if not t_m.lower().endswith("s"):
                                t_m = t_m[:-1] + "ies" if t_m.endswith("y") else t_m + "s"
                            rep = f"`{t_w}` ({t_m})"
                        elif not rep.lower().endswith(("s", "ḥ", "aḥ", "āḥ", ")")):
                            rep = rep[:-1] + "ies" if rep.endswith("y") else rep + "s"
                    if rep.lower().startswith("the ") and art.lower().startswith("the "):
                        art = ""
                    return (art if keep_article else "") + rep
                if gloss_for is not None:
                    pref_m = PREFIX_ONLY_RE.match(m.group(0))
                    core = m.group(0)[len(pref_m.group(1)) if pref_m else 0:]
                    text = text[: m.start()] + sub(m) + text[m.end():]
                    return text, core
                if every:                                 # every alternative of the list, not the first that occurs
                    text = pat.sub(sub, text)
                    spans = _protected(text)
                    first = first or phrase
                    continue
                text = text[: m.start()] + sub(m) + text[m.end():]
            return text, phrase
    return (text, first) if first else None
