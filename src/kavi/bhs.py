"""Buddhist Hybrid Sanskrit: the readings of a hybrid form as classical Sanskrit, after Edgerton's Grammar (1953).

A BHS form is looked up as it stands first; when the dictionary does not know it, these rules propose the classical
forms it may stand for, each with the paragraph of Edgerton's *Buddhist Hybrid Sanskrit Grammar* that describes the
change (``Edg. § 8.108``), so that the analysis can say what the reading rests on. The rules are the systematic ones:
the manuscript spellings (anusvāra for a nasal before a stop, a consonant doubled after ``r``, ``satva`` for ``sattva``),
the Middle Indic endings (nominative ``-o``/``-u``, instrumental plural ``-ehi``, genitive plural ``-āna``, locative
``-asmiṃ``/``-aṃhi``), the optative in ``-eya``, the gerund in ``-tvāna``/``-iya``. A form may have several readings; the
caller ranks them by what the dictionary knows.
"""

from __future__ import annotations

import re

# (pattern on the IAST form, replacement, Edgerton §, note) — applied one at a time; the result is a candidate
RULES: list[tuple[str, str, str, str]] = [
    # spelling
    (r"ṃ([kg])", r"ṅ\1", "§ 2.64", "anusvāra for the class nasal before a stop"),
    (r"ṃ([cj])", r"ñ\1", "§ 2.64", "anusvāra for the class nasal before a stop"),
    (r"ṃ([ṭḍ])", r"ṇ\1", "§ 2.64", "anusvāra for the class nasal before a stop"),
    (r"ṃ([td])", r"n\1", "§ 2.64", "anusvāra for the class nasal before a stop"),
    (r"ṃ([pb])", r"m\1", "§ 2.64", "anusvāra for the class nasal before a stop"),
    (r"([aeiouāīū])kk(r|l)", r"\1k\2", "§ 2.78", "consonant doubled before r"),
    (r"satv", "sattv", "§ 2.84", "single for double consonant (satva for sattva)"),
    (r"([ṅñṇnm])([kgcjṭḍtdpb])\2", r"\1\2", "§§ 2.74–80", "consonant doubled after a nasal (law of morae)"),
    (r"([ṛr])([kgcjṭḍtdpbśṣsmnyv])\2", r"\1\2", "§ 2.78", "consonant doubled after r"),
    (r"ṛ(?=[yḥsṃśṣ])", "ri", "§ 3.94", "ṛ written for ri (kṛyā, tṛḥ, tṛsāhasra)"),
    (r"ṃm$", "m", "§ 2.64", "anusvāra written before a final m"),
    (r"ṃ([ṅñṇnm])", r"\1", "§ 2.64", "anusvāra written before a nasal"),
    (r"hṇ", "hn", "§ 2.39", "ṇ for n after h (madhyāhṇa)"),
    (r"āyusm", "āyuṣm", "§ 2.30", "s written for ṣ in āyuṣmat"),
    (r"sahastra", "sahasra", "§ 2.1", "stra written for sra in sahasra"),
    (r"āstrav", "āsrav", "§ 2.1", "stra written for sra in āsrava"),
    (r"ṇh", "hṇ", "§ 2.39", "ṇh written for hṇ by metathesis (pūrvāṇha for pūrvāhṇa)"),
    (r"ṇh", "hn", "§ 2.39", "ṇh written for hn by metathesis, the nasal made retroflex (madhyāṇha for madhyāhna)"),
    (r"bhi$", "bhiḥ", "§ 2.62", "loss of visarga in instrumental plural -bhi"),
    (r"āyaṃ$", "āyām", "§ 9.68", "locative singular feminine in -āyaṃ"),
    (r"uṃ$", "u", "§ 12.28", "neuter accusative singular in -uṃ (vastuṃ)"),
    (r"iṃ$", "i", "§ 10.45", "neuter accusative singular in -iṃ"),
    (r"īye$", "yāḥ", "§ 10.78", "oblique singular feminine in -īye"),
    (r"īya$", "yāḥ", "§ 10.79", "oblique singular feminine in -īya"),
    (r"ūye$", "vāḥ", "§ 12.31", "oblique singular feminine in -ūye"),
    (r"īhi$", "ībhiḥ", "§ 10.193", "instrumental plural in -īhi"),
    (r"ūhi$", "ūbhiḥ", "§ 12.63", "instrumental plural in -ūhi"),
    (r"īnaṃ$", "īnām", "§ 10.200", "genitive plural in -īnaṃ"),
    (r"ūnaṃ$", "ūnām", "§ 12.68", "genitive plural in -ūnaṃ"),
    # nouns, a-stems (chapter 8)
    (r"o$", "aḥ", "§ 8.18", "nominative singular in -o"),
    (r"u$", "aḥ", "§ 8.20", "nominative singular in -u"),
    (r"asmiṃ$", "e", "§ 8.63", "locative singular in -asmiṃ"),
    (r"asmin$", "e", "§ 8.63", "locative singular in -asmin"),
    (r"aṃhi$", "e", "§ 8.61", "locative singular in -aṃhi"),
    (r"ehi$", "aiḥ", "§ 8.108", "instrumental plural in -ehi"),
    (r"ebhi$", "aiḥ", "§ 8.109", "instrumental plural in -ebhi"),
    (r"āna$", "ānām", "§ 8.124", "genitive plural in -āna"),
    (r"ānaṃ$", "ānām", "§ 8.123", "genitive plural in -ānaṃ"),
    (r"āto$", "āt", "§ 8.50", "ablative singular in -āto"),
    (r"ato$", "āt", "§ 8.53", "ablative singular in -ato"),
    (r"asmā$", "āt", "§ 8.57", "ablative singular in -asmā"),
    (r"asyā$", "asya", "§ 8.58", "genitive singular in -asyā"),
    (r"e$", "aḥ", "§ 8.25", "nominative singular in -e (Māgadhism)"),
    (r"āye$", "āyai", "§ 9.44", "dative singular feminine in -āye"),
    (r"āya$", "āyāḥ", "§ 9.49", "oblique singular feminine in -āya"),
    # verbs
    (r"eya$", "et", "§ 29.28", "optative in -eya"),
    (r"eyā$", "et", "§ 29.28", "optative in -eyā"),
    (r"eyaṃ$", "eyam", "§ 29.8", "optative first singular"),
    (r"etsuḥ$", "eyuḥ", "§ 29.18", "optative third plural in -etsuḥ"),
    (r"tvāna$", "tvā", "§ 35.5", "gerund in -tvāna"),
    (r"itvāna$", "itvā", "§ 35.29", "gerund in -itvāna"),
    (r"itva$", "itvā", "§ 35.12", "gerund in -itva with final vowel shortened"),
    (r"^dvimocay", "vimocay", "§ 4.64", "external sandhi d- carried over line break (mahābhayād vimocaye)"),
    (r"^āgamī$", "āgamiṣyati", "§ 31.2", "future third singular in -ī on the root ā-gam (āgacchati)"),
    (r"^(punar|antar|prātar)a[ṃm]$", r"\1", "§ 4.61", "thematic nasal extension -aṃ on indeclinable in -r"),
    (r"^kiddaś", "kīdṛś", "§ 3.90", "Middle Indic kiddaśa for kīdṛśa"),
    (r"^śrāvasy", "śrāvasty", "§ 2.12", "cluster simplification in śrāvastyām"),
    (r"āyuṣmānānd", "āyuṣmānānand", "§ 4.59", "haplology in āyuṣmān ānanda"),
    (r"^bhūvan$", "abhūvan", "§ 32.105", "augmentless abhūvan"),
    (r"prādurbhūvan$", "prādurabhūvan", "§ 32.105", "augmentless prādurabhūvan"),
    (r"iya$", "ya", "§ 35.8", "gerund in -iya"),
    (r"iyāna$", "ya", "§ 35.45", "gerund in -iyāna"),
    (r"iṃsu$", "iṣuḥ", "§ 32.95", "aorist third plural in -iṃsu"),
    (r"iṃsuḥ$", "iṣuḥ", "§ 32.96", "aorist third plural in -iṃsuḥ"),
    (r"etsu$", "eyuḥ", "§ 29.18", "optative third plural in -etsu"),
    (r"ohi$", "u", "§ 30.2", "imperative second singular in -ohi"),
    (r"āhi$", "a", "§ 30.2", "imperative second singular in -āhi"),
    (r"ati$", "anti", "§ 28.3", "third singular -ati for third plural -anti"),
    (r"et$", "eta", "§ 37.10", "active for middle ending (bhāṣet for bhāṣeta)"),
    (r"ate$", "ati", "§ 37.24", "middle for active ending (janayate for janayati)"),
    (r"ante$", "anti", "§ 37.24", "middle for active ending (bhavante for bhavanti)"),
    (r"se$", "si", "§ 37.25", "middle for active ending (pravadase for pravadasi)"),
    (r"gṛhīṣy", "grahīṣy", "§ 31.10", "future gṛhīṣyati for grahīṣyati"),
    (r"yāmi$", "ye", "§ 37.22", "active ending on the ya-stem (adhimucyāmi for adhimucye)"),
    (r"yati$", "yate", "§ 37.22", "active ending on the ya-stem"),
    (r"yanti$", "yante", "§ 37.22", "active ending on the ya-stem"),
    # stems in -ant (chapter 18)
    (r"^([yt]āva)ṃt(?=[yī])", r"\1t", "§ 18.1", "the feminine yāvantī for yāvatī"),
    (r"^([yt]āva)nt(?=[yī])", r"\1t", "§ 18.1", "the feminine yāvantī for yāvatī"),
]


def readings(form: str, max_depth: int = 2) -> list[tuple[str, str]]:
    """Candidate classical forms for a hybrid ``form`` (IAST, lower case), each with the rules applied:
    ``[("bhavet", "§ 29.28 optative in -eya"), …]``, nearest first. The form itself is not included."""
    out: list[tuple[str, str]] = []
    seen = {form}
    frontier = [(form, "")]
    for _ in range(max_depth):
        nxt = []
        for f, why in frontier:
            for pat, rep, par, note in RULES:
                g = re.sub(pat, rep, f)
                if g != f and g not in seen:
                    seen.add(g)
                    tag = f"{par} {note}" if not why else f"{why}; {par} {note}"
                    out.append((g, tag))
                    nxt.append((g, tag))
        frontier = nxt
    return out
