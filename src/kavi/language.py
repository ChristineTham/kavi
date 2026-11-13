"""The source language: Pāli (the default) or Sanskrit. One shared record that the modules read."""

from __future__ import annotations

# Kaccāyana's sabbanāma (Appendix L of the textbook), which take the pronoun mark whatever the DPD calls them.
SABBANAMA = {"sabba", "katara", "katama", "ubhaya", "itara", "añña", "aññatara", "aññatama", "pubba", "para", "apara",
             "dakkhiṇa", "uttara", "adhara", "ya", "ta", "eta", "ima", "amu", "kiṃ", "eka", "tumha", "amha", "ahaṃ", "tvaṃ"}

LANGUAGE = {"name": "Pāli", "code": "pi", "niggahita": True}
PRONOUNS: set[str] = set(SABBANAMA)

# The small words a draft is apt to drop, by the stem the lexicons give, with their English (one word; two where the reference
# uses both). The discourse prompt shows each beside its word in the text, because a hint on the word is obeyed where "drop no
# particle" and a list far away are not.
PARTICLES = {
    "sa": {"api": "too / even", "iva": "like", "eva": "indeed", "ca": "and", "vā": "or", "tu": "but", "hi": "for / indeed", "khalu": "indeed",
           "kila": "indeed", "nāma": "by name", "aho": "oh", "bata": "alas"},
    "pi": {"pi": "too / even", "iva": "like", "eva": "indeed", "ca": "and", "vā": "or", "tu": "but", "hi": "for / indeed", "kho": "indeed",
           "kira": "it is said", "nāma": "by name", "pana": "but", "aho": "oh"},
}


def particles() -> dict[str, str]:
    return PARTICLES.get(LANGUAGE["code"], {})


# The oblique cases of the pronouns a draft drops (tasya, tvayi) or takes for the subject (an accusative): the English of stem,
# case and number, shown beside the word in the discourse prompt like a particle's. Personal pronouns and tad, Sanskrit only,
# and never a nominative (braces on every tvam made a model stop writing its epithets in form). The instrumental and ablative
# of tad are also the adverbs "therefore" and "from there", so both are given. The enclitics, in the forms a text shows,
# read too many ways to place.
PRONOUN_STEMS = {"sa": {"asmad": ("me", "us"), "yuṣmad": ("you", "you"), "tad": ("him / that", "them")}}
PRONOUN_FRAMES = {"acc": "{}, object", "instr": "by {}", "dat": "to {}", "abl": "from {}", "gen": "of {}", "loc": "in {}"}
ENCLITICS = {"me", "te", "mā", "tvā", "nas", "vas", "naḥ", "vaḥ", "no", "vo"}
# the relative pronoun, in the cases where it is a pronoun and not a conjunction (yena, yasmāt are "whereby", "because"; the neuter
# nominative and accusative yad is "that", "because", "which": the clause decides)
RELATIVE_FRAMES = {"nom": "who / which", "acc": "whom / which", "dat": "to whom / to which", "gen": "of whom / of which",
                   "loc": "in whom / in which"}


def pronoun_english(stem: str, case: str, number: str, gender: str = "") -> str:
    """tvām -> "you, object", tasya -> "of him / that", tasyāḥ -> "of her / that", yasya -> "of whom / of which"; nothing for
    a form it cannot place."""
    if stem == "yad" and LANGUAGE["code"] == "sa":
        return "" if gender == "nt" and case in ("nom", "acc") else RELATIVE_FRAMES.get(case, "")
    forms = PRONOUN_STEMS.get(LANGUAGE["code"], {}).get(stem)
    if not forms or number not in ("sg", "pl") or case not in PRONOUN_FRAMES:
        return ""
    if stem == "tad" and gender == "fem":
        forms = ("her / that", "them")
    elif stem == "tad" and case in ("instr", "abl") and number == "sg":
        return "by that / therefore" if case == "instr" else "from that / therefore"    # tena, tasmāt: the clause decides
    return PRONOUN_FRAMES[case].format(forms[0 if number == "sg" else 1])


def set_language(lexicon) -> None:
    """Pāli or Sanskrit, by the lexicon in use: the name the prompts use, the spelling of the nasal, the pronoun list."""
    if isinstance(lexicon, str):                       # "sa" or "pi", for a script without a lexicon in hand
        if lexicon in ("sa", "sanskrit", "Sanskrit"):
            from .sanskrit import SanskritLexicon as lexicon
        else:
            lexicon = None
    LANGUAGE["name"] = getattr(lexicon, "language", "Pāli")
    LANGUAGE["code"] = getattr(lexicon, "code", "pi")
    LANGUAGE["niggahita"] = LANGUAGE["code"] == "pi"
    PRONOUNS.clear()
    PRONOUNS.update(getattr(lexicon, "pronouns", None) or SABBANAMA)


def language_name() -> str:
    return LANGUAGE["name"]
