"""What to leave in Pāḷi.

Three classes of word are handled specially in the prompts:

* **names** — people, places, texts: kept untranslated (in their stem form);
* **honorifics and epithets** — `bhante`, `āvuso`, `bhagavā`: kept untranslated;
* **technical terms** — words the text uses as terms of art: kept in Pāḷi with a short English gloss in
  parentheses on first use, `khandha` (aggregate).

The DPD marks most of these through its *family sets* and its "name of …" meanings; a short curated list
covers the everyday doctrinal vocabulary that carries no set. The lists are advisory: the prompt asks the
model to apply them only where the word is used as a term, so that an ordinary sentence about a heap of
grain does not come out as `khandha` (aggregate). A capitalised word inside a sentence that the DPD does not
know is reported as a probable name (Roman-script editions capitalise names). A user glossary
(``--glossary``, lines of ``term: gloss``) adds terms for a particular text, such as a grammar's vocabulary.
"""

from __future__ import annotations

import re

# Words that are honorifics or forms of address, however they are inflected.
HONORIFICS = {
    "bhante", "bhadante", "āvuso", "ayya", "ayyo", "ayye", "ayyā", "bhagavā", "bhagavant", "bhagavantu",
    "sugata", "tathāgata", "sammāsambuddha", "sammāsambuddho", "satthā", "satthar", "mārisa", "bho", "bhoto", "bhavaṃ",
    "bhavant", "deva", "mahārāja", "ayyaputta", "ācariya", "upajjhāya", "thera", "therī", "mahāthera",
    # monastic and lay titles are left as they stand in the text (bhikkhave, bhikkhū), with no gloss
    "bhikkhu", "bhikkhunī", "sāmaṇera", "sāmaṇerī", "upāsaka", "upāsikā", "samaṇa", "brāhmaṇa", "paribbājaka",
    "arahant", "arahanta", "tathāgata", "sammāsambuddha", "buddha", "sāvaka", "sekha", "asekha",
}

# Everyday doctrinal vocabulary the DPD does not put in a set (stems, as the DPD lemma has them).
CORE_TERMS = {
    "dhamma", "saṅgha", "nibbāna", "kamma", "khandha", "jhāna", "samādhi", "paññā", "sīla", "dukkha", "anicca",
    "anattā", "taṇhā", "āsava", "bodhisatta", "sutta", "vinaya",
    "abhidhamma", "sati", "vipassanā", "samatha", "mettā", "karuṇā", "muditā", "upekkhā", "bodhi", "saṃsāra",
    "vipāka", "kilesa", "nīvaraṇa", "bojjhaṅga", "indriya", "iddhipāda", "satipaṭṭhāna", "magga", "phala",
    "sotāpanna", "sakadāgāmī", "anāgāmī", "ariya", "puthujjana", "paramattha", "sammuti", "nāmarūpa",
    "viññāṇa", "vedanā", "saññā", "saṅkhāra", "āyatana", "paṭiccasamuppāda", "nidāna", "avijjā",
    "upādāna", "bhava", "phassa", "saḷāyatana", "uposatha", "pātimokkha", "kammaṭṭhāna", "kasiṇa",
    "brahmavihāra", "pāramī", "pāramitā", "paccekabuddha", "dāna",
    "puñña", "pāpa", "akusala", "kusala", "cetanā", "citta", "cetasika", "manasikāra", "yoniso", "papañca",
    "diṭṭhi", "micchādiṭṭhi", "sammādiṭṭhi", "vīriya", "viriya", "khanti", "sacca", "adhiṭṭhāna", "nekkhamma",
    "vimutti", "vimokkha", "suññatā", "animitta", "appaṇihita", "sakkāya", "vicikicchā", "sīlabbata", "kāmarāga",
    "paṭigha", "māna", "uddhacca", "moha", "lobha", "dosa", "rāga", "kāma", "byāpāda", "vihiṃsā", "nekkhamma",
    "sammāvācā", "sammākammanta", "sammāājīva", "sammāvāyāma", "sammāsati", "sammāsamādhi", "sammāsaṅkappa",
    "anussati", "ānāpānassati", "kāyagatāsati", "asubha", "maraṇassati", "deva", "brahmā", "māra", "yakkha",
    "nāga", "peta", "asura", "gandhabba", "niraya", "sagga", "sīmā", "kathina", "pavāraṇā", "vassa", "gāthā",
}

# DPD family sets whose members are names, titles of texts, or other things left untranslated.
NAME_SETS = re.compile(
    r"^names of |place names|villages, towns|names of rivers|names of mountains|names of countries|"
    r"names of monasteries|family names|holy sites|^Sri Lanka$|names of hells|names of heavens|"
    r"names of continents|great disciples|chief disciples|previous Buddhas|six ascetic teachers|"
    r"daughters of Mara|^suttas of|^vaggas of|^books of|^chapters of|^parts of|^saṃyuttas of|^sections of|"
    r"^commentaries$|^grammars$|names of books|^people$|^five Mārā$|^pureland deities$"
)
HONORIFIC_SETS = re.compile(r"^epithets of (the Buddha|arahants|Sakka|Māra|devas)$")
TECH_SETS = re.compile(
    r"^doctrines$|five aggregates|five hindrances|noble paths and fruits|epithets of Nibbāna|types of ariyas|"
    r"nine attainments|formless attainments|five liberations|five eyes|three eyes|four bonds|cattāro oghā|"
    r"three realms of existence|four modes of generation|32 marks|types of monastics|types of ascetics|"
    r"types of supernatural beings|epithets of stream entry|bhikkhupātimokkha rules|vinaya offences|"
    r"nine types of suttas|reasons for a discourse|seven treasures"
)


# Honorifics written with a capital (the user's style: "the Bhagavā's words", but "the bhikkhū", "bhikkhave").
CAPITALISED_HONORIFICS = {"bhagavā", "bhagavant", "bhagavantu", "satthā", "satthar", "tathāgata", "sugata", "sammāsambuddha",
                          "buddha", "jina", "bhante", "bhadante"}


def honorific_form(stem: str, surface: str, parses: list[str], family_set: str = "") -> str:
    """How an honorific is written in the English: as it stands when nominative or vocative, otherwise in its
    citation form (the stem), capitalised for the epithets of the Buddha and the forms of address."""
    form = surface
    if stem.startswith("bhagavant") or stem == "bhagavā":
        form = "bhagavā"
    elif parses and not any(("nom" in p or "voc" in p) for p in parses):
        form = stem
    if stem in CAPITALISED_HONORIFICS or "epithets of the Buddha" in family_set:
        form = form[:1].upper() + form[1:]
    return form


def term_form(stem: str, surface: str, parses: list[str]) -> str:
    """A technical term is shown as it stands in the text when nominative or vocative (`viññāṇaṃ`), otherwise
    in its stem form (`dhamma` for dhammassa) — the user's practice."""
    if parses and not any(("nom" in p or "voc" in p) for p in parses):
        return stem
    return surface


def classify(stem: str, meaning: str, family_set: str) -> str:
    """'name', 'honorific', 'technical' or '' for one DPD headword."""
    sets = [s for s in family_set.split("; ") if s]
    low = meaning.lower()
    if stem in HONORIFICS or any(HONORIFIC_SETS.search(s) for s in sets):
        return "honorific"
    if low.startswith("name of") or low.startswith("(name of") or any(NAME_SETS.search(s) for s in sets):
        return "name"
    if stem in CORE_TERMS or any(TECH_SETS.search(s) for s in sets):
        return "technical"
    return ""
