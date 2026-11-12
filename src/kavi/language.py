"""The source language: Pāli (the default) or Sanskrit. One shared record that the modules read."""

from __future__ import annotations

# Kaccāyana's sabbanāma (Appendix L of the textbook), which take the pronoun mark whatever the DPD calls them.
SABBANAMA = {"sabba", "katara", "katama", "ubhaya", "itara", "añña", "aññatara", "aññatama", "pubba", "para", "apara",
             "dakkhiṇa", "uttara", "adhara", "ya", "ta", "eta", "ima", "amu", "kiṃ", "eka", "tumha", "amha", "ahaṃ", "tvaṃ"}

LANGUAGE = {"name": "Pāli", "code": "pi", "niggahita": True}
PRONOUNS: set[str] = set(SABBANAMA)


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
