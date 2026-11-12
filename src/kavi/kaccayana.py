"""Rules from Mahākaccāyana's *Kaccāyanabyākaraṇaṃ* (https://kaccayana.github.io) for Pāḷi analysis.

Alongside Pāṇini's *Aṣṭādhyāyī* (:mod:`kavi.panini`) for Sanskrit and Edgerton's *Buddhist Hybrid Sanskrit Grammar*
(:mod:`kavi.bhs`), this module codifies Mahākaccāyana's classical grammatical rules across six domains:

* **Sandhikappa** (§1–§51): Sound junctions, elision of vowels (§12 ``sarā sare lopaṃ``, §13 ``vā paro asarūpā``),
  qualitative vowel change (§14 ``kvacāsavaṇṇaṃ lutte``), lengthening (§15 ``dīghaṃ``), consonantalization
  (§17 ``yamedantassādeso``, §18 ``vamodudantānaṃ``), euphonic consonant augments (§35 ``ya va ma da na ta ra lā cāgamā``),
  gemination (§28 ``para dvebhāvo ṭhāne``), and prefix assimilation (§44 ``abbho abhi``, §45 ``ajjho adhi``,
  §47 ``atissa canatassa``);
* **Nāmakappa** (§52–§270): Declension classes, stem alternations, and the *mano-gaṇa* consonant stems
  (§197–§205: *manas*, *cetas*, *tapas*, *yasas*, *tejas*, *vācas*, *vayas*, *āyus*, *payas*, *sarad*) inflecting with
  nominative/accusative ``-o``, instrumental ``-asā``, genitive/dative ``-aso``, and compound stem ``-o-``;
* **Kārakakappa** (§271–§315): The syntactic relations between nouns and verbal action: the six *kārakas*
  (*kattā* §281, *kamma* §280, *karaṇa* §279, *sampadāna* §276, *apādāna* §271, *okāsa/ādhāra* §278) and two
  non-kāraka relations (*sāmī* §283, *ālapana* §285), with specific case government rules (§287 *saha-yoge*,
  §294 *namādi-yoge*, §282 *bhayādi-yoge*, §298 *kālādhānam accantasamyoge*, §304 *niddhāraṇa*, §313 *bhāvalakkhaṇa*);
* **Samāsakappa** (§316–§343): Compounds: inflection elision (§317 ``tesaṃ vibhattiyo lopā ca``), stem reversion
  (§318 ``pakati cassa saranto``), the six compound classes (*abyayībhāva* §319–320, *kammadhāraya* §324, *digu* §325,
  *tappurisa* §327, *bahubbīhi* §328, *dvanda* §329), prefix alterations (§330 ``mahantaṃ mahā vante``, §333 ``nassa no
  vā sare ana``), *samāsānta* final stem changes (§335: *rāja* $\\rightarrow$ *rājan*, *sakha* $\\rightarrow$ *sakhi*,
  *akkha* $\\rightarrow$ *akkhi*), junction lengthening (§337 ``dīgho``), and neuter shortening (§342 ``hrasso``);
* **Taddhitakappa** (§344–§405): Secondary derivations from nominal stems: reverse *vuddhi* (§396, §400: ``ā`` $\\rightarrow$
  ``a``, ``e`` $\\rightarrow$ ``i``, ``o`` $\\rightarrow$ ``u``), relational affixes (§350 ``-ika``, §357 ``-ima``/``-iya``),
  abstract affixes (§360 ``-ya``, §361 ``-tta``/``-tā``), possessive affixes (§364 ``-vantu``/``-mantu``, §365 ``-vī``,
  §367 ``-ī``), composition affixes (§372 ``-maya``), and adverbial affixes (§393 ``-to``, §394 ``-so``);
* **Kibbidhānakappa** (§524–§623): Primary derivations from verbal roots: present participles (§527, §565 ``-anta``,
  ``-māna``), gerundives (§528, §540 ``-tabba``, ``-anīya``, ``-teyya``), agent nouns (§531 ``-aka``, §532 ``-tar``),
  past participles (§555 ``-ta``, §556 ``-na``), infinitives (§561 ``-tuṃ``, ``-tave``), and absolutives (§563 ``-tvā``,
  ``-tvāna``, §597 ``-ya``).
"""

from __future__ import annotations

import re
from typing import NamedTuple

VOWELS = "aāiīuūeo"
SHORT_VOWELS = "aiu"
LONG_VOWELS = "āīūeo"
CONSONANTS = "kgṅcjñṭḍṇtdnpbmyrlvhḷ"

# --------------------------------------------------------------------------------------
# 2. Nāmakappa: Mano-gaṇa Consonant Stems (§197–§205)
# --------------------------------------------------------------------------------------

# Kaccāyana §197 Mano gaṇādito o ā asmā: stems ending in -as that inflect with -o, -ā, -asā
MANOGANA_STEMS: set[str] = {
    "manas",      # mind, thought
    "cetas",      # mind, heart
    "tapas",      # ascetic practice, spiritual heat
    "yasas",      # fame, glory
    "tejas",      # fire, energy, radiance
    "vācas",      # speech, word
    "vayas",      # age, time of life
    "āyus",       # life, longevity
    "payas",      # milk, water
    "sarad",      # autumn, year
    "ura",        # chest (uras)
    "siras",      # head
    "tamas",      # darkness
    "rajas",      # dust, passion
    "āhas",       # day
}

# The DPD lemmata for the mano-gaṇa group
MANOGANA_LEMMAS: dict[str, str] = {
    "mano": "mana",
    "manasā": "mana",
    "manaso": "mana",
    "manasi": "mana",
    "ceto": "ceta",
    "cetasā": "ceta",
    "cetaso": "ceta",
    "cetasi": "ceta",
    "tapo": "tapa",
    "tapasā": "tapa",
    "tapaso": "tapa",
    "yaso": "yasa",
    "yasasā": "yasa",
    "yasaso": "yasa",
    "tejo": "teja",
    "tejasā": "teja",
    "tejaso": "teja",
    "vāco": "vācā",
    "vacasā": "vācā",
    "vayo": "vaya",
    "vayasā": "vaya",
    "āyu": "āyu",
    "āyunā": "āyu",
    "āyuso": "āyu",
}


def is_manogana(stem: str) -> bool:
    """Whether ``stem`` belongs to Kaccāyana's *mano-gaṇa* consonant class (§197)."""
    clean = stem.rstrip("1234567890 ").strip()
    return clean in MANOGANA_STEMS or clean in {"mana", "ceta", "tapa", "yasa", "teja", "vaya", "āyu", "sira", "tama", "raja"}


# --------------------------------------------------------------------------------------
# 4. Samāsakappa: Compound Deconstruction & Morphophonemics (§316–§343)
# --------------------------------------------------------------------------------------

# Kaccāyana §335 Samāsantagatānaṃ kvaci: stem alternations at the end of a compound
SAMASANTA_PALI: dict[str, str] = {
    "rāja": "rājan",     # mahārāja -> mahā + rājan (§335)
    "sakha": "sakhi",    # kalyāṇasakho -> kalyāṇa + sakhi (§335)
    "akkha": "akkhi",    # visālakkho -> visāla + akkhi (§335)
    "aṅgula": "aṅguli",  # dvaṅgula -> dvi + aṅguli (§335)
    "nada": "nadī",      # pañcanadaṃ -> pañca + nadī (§335)
    "aha": "ahan",       # pubbaṇha -> pubba + ahan (§335)
}


def compound_junction_variants_pali(left: str, right: str) -> list[tuple[str, str]]:
    """Morphophonemic reversals at a Pāḷi compound or prefix boundary ``(left, right)``
    following Kaccāyana's Samāsakappa (§316–§343).
    """
    out: list[tuple[str, str]] = [(left, right)]

    # §330 Mahantaṃ mahā vante: mahā- in prior member represents mahanta / mahat
    if left == "mahā":
        out.append(("mahanta", right))
        out.append(("mahat", right))

    # §333 Nassa no vā sare ana: negative particle na becomes an- before vowels, a- before consonants
    if left == "a" and right and right[0] not in VOWELS:
        out.append(("na", right))
    elif left == "an" and right and right[0] in VOWELS:
        out.append(("na", right))

    # §334 Kadiyassa kudo ca: ku- prefix alternates with kad- or kā-
    if left == "ku" and right:
        out.append(("kud", right))
        out.append(("kā", right))

    # §335 Samāsantagatānaṃ kvaci: restore stem forms for final members
    for end, full in SAMASANTA_PALI.items():
        if right == end:
            out.append((left, full))
        elif right.endswith(end) and len(right) > len(end):
            prefix = right[:-len(end)]
            out.append((left, prefix + full))

    # §337 Dīgho: lengthening of final vowel of prior member in compounds
    if left.endswith("ā") and len(left) >= 3:
        out.append((left[:-1] + "a", right))
    elif left.endswith("ī") and len(left) >= 3:
        out.append((left[:-1] + "i", right))
    elif left.endswith("ū") and len(left) >= 3:
        out.append((left[:-1] + "u", right))

    # §197 Mano-gaṇa in compounds: final -as appears as -o- (manomaya -> manas + maya)
    if left.endswith("o") and len(left) >= 3:
        base = left[:-1]
        if base in {"man", "cet", "tap", "yas", "tej", "vac", "vay", "ay"}:
            out.append((base + "as", right))
            out.append((base + "a", right))

    # §342 Hrasso samāsantassa: neuter shortening of final long vowel
    if right.endswith("a") and len(right) >= 3:
        out.append((left, right[:-1] + "ā"))

    return out


# --------------------------------------------------------------------------------------
# 5. Taddhitakappa: Secondary Derivation & Reverse Vuddhi (§344–§405)
# --------------------------------------------------------------------------------------

class TaddhitaProposal(NamedTuple):
    base: str
    suffix: str
    rule: str
    meaning: str


def undo_initial_vuddhi_pali(stem: str) -> list[str]:
    """Kaccāyana §396/§400: reverse initial *vuddhi* (strengthening) to recover the base
    nominal stem of a *taddhita* derivative:
    - ``ā`` -> ``a`` (vāsiṭṭha -> vasiṭṭha, sāṅghika -> saṅgha, mānasika -> manas)
    - ``e`` -> ``i`` (venateyya -> vinatā, vesāmitta -> visāmitta)
    - ``o`` -> ``u`` (kosalla -> kusala, gotama -> gutama/guta, opapātika -> upapāta)
    """
    m = re.match(r"^([^aāiīuūeo]*)(ā|e|o)(.+)$", stem)
    if not m:
        return []
    ons, v, rest = m.group(1), m.group(2), m.group(3)
    out: list[str] = []
    if v == "ā":
        out.append(ons + "a" + rest)
    elif v == "e":
        out.append(ons + "i" + rest)
    elif v == "o":
        out.append(ons + "u" + rest)
    return out


def undo_taddhita_pali(word: str) -> list[TaddhitaProposal]:
    """Propose underlying base nominal stems and Kaccāyana *taddhita* suffixes for ``word``."""
    out: list[TaddhitaProposal] = []

    def add_prop(b: str, sfx: str, rule: str, desc: str, apply_vuddhi: bool = False):
        if len(b) < 2:
            return
        # If the base ends in a consonant (e.g. dhamm- from dhammika), propose a-stem and ā-stem
        stems = [b]
        if b[-1] not in VOWELS:
            stems.append(b + "a")
            stems.append(b + "ā")
        for s in stems:
            out.append(TaddhitaProposal(s, sfx, rule, desc))
            if apply_vuddhi:
                for v_base in undo_initial_vuddhi_pali(s):
                    out.append(TaddhitaProposal(v_base, sfx, rule + "+vuddhi", desc))

    # §350 Ṇika: -ika relational/occupational (dhammika -> dhamma, maggika -> magga)
    if word.endswith(("ika", "iko", "ikaṃ", "ikā", "ike", "ikānaṃ")):
        base = re.sub(r"ik[oāaṃe]?$|ikānaṃ$", "", word)
        add_prop(base, "-ika", "§350 Ṇika", "pertaining to / living by", apply_vuddhi=True)

    # §361 Tta, tā: abstract noun forming suffixes (manussatta -> manussa, lahutā -> lahu)
    if word.endswith(("tta", "ttaṃ", "ttena", "ttāya")):
        base = re.sub(r"tt(aṃ|a|ena|āya)$", "", word)
        add_prop(base, "-tta", "§361 Tta", "the state or quality of (-ness)")
    if word.endswith(("tā", "tāya", "tāyaṃ")):
        base = re.sub(r"tā(ya|yaṃ)?$", "", word)
        add_prop(base, "-tā", "§361 Tā", "the state or quality of (-ness)")

    # §364 Vantu, mantu: possessive suffixes (guṇavantu -> guṇa, satimantu -> sati)
    if word.endswith(("vantu", "vant", "vā", "vanto", "vantaṃ", "vantena")):
        base = re.sub(r"(vant(?:ena|aṃ|u|o|a)?|vā)$", "", word)
        add_prop(base, "-vantu", "§364 Vantu", "possessing / endowed with")
    if word.endswith(("mantu", "mant", "mā", "manto", "mantaṃ", "mantena")):
        base = re.sub(r"(mant(?:ena|aṃ|u|o|a)?|mā)$", "", word)
        add_prop(base, "-mantu", "§364 Mantu", "possessing / endowed with")

    # §367 Ī: possessive suffix (sukhī -> sukha, dhammī -> dhamma, daṇḍī -> daṇḍa)
    if word.endswith(("ī", "ino", "inaṃ", "inā")):
        base = re.sub(r"(ī|in(?:aṃ|o|a|ā)?)$", "", word)
        add_prop(base, "-ī", "§367 Ī", "having / characterized by")

    # §372 Maya: material / made of (suvaṇṇamaya -> suvaṇṇa, manomaya -> manas)
    if word.endswith(("maya", "mayo", "mayaṃ", "mayā")):
        base = re.sub(r"may(aṃ|o|a|ā)$", "", word)
        add_prop(base, "-maya", "§372 Maya", "made of / consisting of")

    # §393 To: ablative adverbial suffix (sabbato -> sabba, aññato -> añña, piṭṭhito -> piṭṭhi)
    if word.endswith("to") and len(word) >= 4:
        base = word[:-2]
        add_prop(base, "-to", "§393 To", "from / on the side of (ablative adverb)")

    # §394 So: distributive adverbial suffix (sabbaso, bhāgaso, padaso)
    if word.endswith("so") and len(word) >= 4:
        base = word[:-2]
        add_prop(base, "-so", "§394 So", "by way of / -wise (distributive adverb)")

    return out


# --------------------------------------------------------------------------------------
# 3. Kārakakappa: Syntactic Cases & Semantic Roles (§271–§315)
# --------------------------------------------------------------------------------------

class KarakaRole(NamedTuple):
    pali_name: str
    english_role: str
    vibhatti_num: int
    case_name: str
    preposition: str
    kaccayana_sutta: str
    description: str


KARAKA_ROLES: dict[str, KarakaRole] = {
    "nom": KarakaRole(
        pali_name="kattā / lingattha",
        english_role="agent / subject",
        vibhatti_num=1,
        case_name="paṭhamā",
        preposition="",
        kaccayana_sutta="§281 Kattari ca / §284 Liṅgatthe paṭhamā",
        description="The agent of an active verb or the bare meaning of the uninflected noun stem.",
    ),
    "voc": KarakaRole(
        pali_name="ālapana",
        english_role="address / vocative",
        vibhatti_num=1,
        case_name="ālapanā paṭhamā",
        preposition="O",
        kaccayana_sutta="§285 Ālapane ca",
        description="Direct address.",
    ),
    "acc": KarakaRole(
        pali_name="kamma",
        english_role="patient / direct object / duration",
        vibhatti_num=2,
        case_name="dutiyā",
        preposition="",
        kaccayana_sutta="§280 Kamme dutiyā / §298 Kālādhānam accantasamyoge",
        description="The entity directly affected by the action, destination of motion, or continuous duration.",
    ),
    "inst": KarakaRole(
        pali_name="karaṇa / anabhihita-kattā",
        english_role="instrument / passive agent",
        vibhatti_num=3,
        case_name="tatiyā",
        preposition="by / with",
        kaccayana_sutta="§279 Karaṇe tatiyā / §288 Anabhihite kattari tatiyā",
        description="The instrument or means by which an action is done, or the agent in passive constructions.",
    ),
    "dat": KarakaRole(
        pali_name="sampadāna",
        english_role="recipient / purpose / beneficiary",
        vibhatti_num=4,
        case_name="catutthī",
        preposition="to / for",
        kaccayana_sutta="§276 Sampadāne catutthī / §294 Namādi-yoge",
        description="The recipient of giving, beneficiary, or purpose of an action.",
    ),
    "abl": KarakaRole(
        pali_name="apādāna",
        english_role="source / departure / cause",
        vibhatti_num=5,
        case_name="pañcamī",
        preposition="from / out of",
        kaccayana_sutta="§271 Apādāne pañcamī / §282 Bhayādi-yoge",
        description="The point of departure, origin, source of fear, or cause.",
    ),
    "gen": KarakaRole(
        pali_name="sāmī / sambandha",
        english_role="possessor / relation",
        vibhatti_num=6,
        case_name="chaṭṭhī",
        preposition="of",
        kaccayana_sutta="§283 Sāmismim chaṭṭhī / §304 Niddhāraṇe",
        description="The owner, possessor, partitive whole, or entity standing in relation.",
    ),
    "loc": KarakaRole(
        pali_name="okāsa / ādhāra",
        english_role="location / time / circumstance",
        vibhatti_num=7,
        case_name="sattamī",
        preposition="in / on / at",
        kaccayana_sutta="§278 Okāse sattamī / §313 Bhāvena bhāvalakkhaṇa",
        description="The location in space, container, point in time, or absolute circumstance.",
    ),
}


def karaka_for_case(case: str) -> KarakaRole | None:
    """Return the Kaccāyana *kāraka* definition and English preposition for a case tag."""
    c = case.lower().strip()
    for key, role in KARAKA_ROLES.items():
        if key in c or role.case_name in c:
            return role
    return None


# --------------------------------------------------------------------------------------
# 7. Kibbidhānakappa: Primary Derivation (Kita Suffixes) (§524–§623)
# --------------------------------------------------------------------------------------

class KitakaProposal(NamedTuple):
    stem: str
    suffix: str
    category: str
    rule: str


def decompose_kitaka_pali(word: str) -> list[KitakaProposal]:
    """Propose primary verbal derivations (*kita* affixes) following Kaccāyana §524–§623."""
    out: list[KitakaProposal] = []

    # §527/§565 Anta, Māna: present active & middle/passive participles
    if word.endswith(("anta", "anto", "antaṃ", "antā", "onta", "onto", "ontaṃ", "enta", "ento", "entaṃ")):
        base = re.sub(r"(ant|ont|ent)(?:aṃ|o|a|ā)?$", "", word)
        out.append(KitakaProposal(base, "-anta", "present participle (prp)", "§527 Anta"))
    if word.endswith(("māna", "māno", "mānaṃ", "mānā")):
        base = re.sub(r"mān(?:aṃ|o|a|ā)?$", "", word)
        out.append(KitakaProposal(base, "-māna", "present middle participle (prp)", "§565 Māna"))

    # §528/§540 Tabba, Anīya, Neyya: future passive participles / gerundives (fpp)
    if word.endswith(("tabba", "tabbo", "tabbaṃ", "tabbā")):
        base = re.sub(r"tabb(?:aṃ|o|a|ā)?$", "", word)
        out.append(KitakaProposal(base, "-tabba", "gerundive (fpp)", "§528 Tabba"))
    if word.endswith(("anīya", "anīyo", "anīyaṃ", "anīyā", "aṇīya", "aṇīyo", "aṇīyaṃ", "aṇīyā")):
        base = re.sub(r"a[nṇ]īy(?:aṃ|o|a|ā)?$", "", word)
        out.append(KitakaProposal(base, "-anīya", "gerundive (fpp)", "§540 Anīya"))
    if word.endswith(("teyya", "teyyo", "teyyaṃ")):
        base = re.sub(r"teyy(?:aṃ|o|a)?$", "", word)
        out.append(KitakaProposal(base, "-teyya", "gerundive (fpp)", "§540 Neyya"))

    # §531 Ṇvu -> aka: agent nouns (kāraka, dāyaka, sāvaka)
    if word.endswith(("aka", "ako", "akaṃ", "ikā")):
        base = re.sub(r"[ai]k(?:aṃ|o|a|ā)?$", "", word)
        out.append(KitakaProposal(base, "-aka", "agent noun", "§531 Ṇvu -> §622 aka"))

    # §532 Tu -> tar: agent nouns (satthar, kattar, dātar)
    if word.endswith(("tā", "tāraṃ", "tāro", "tuno", "tari")):
        base = re.sub(r"(tā|tāraṃ|tāro|tuno|tari)$", "", word)
        out.append(KitakaProposal(base, "-tar", "agent noun", "§532 Tu -> tar"))

    # §555 Ta, §556 Na: past participles (pp)
    if word.endswith(("ta", "to", "taṃ", "tā", "te", "tasmā", "tasmiṃ")):
        base = re.sub(r"t(asmā|asmiṃ|o|aṃ|a|ā|e)$", "", word)
        if len(base) >= 2:
            out.append(KitakaProposal(base, "-ta", "past participle (pp)", "§555 Ta"))
    if word.endswith(("na", "no", "naṃ", "nā", "nne", "nno", "nnaṃ", "nnā")):
        base = re.sub(r"(nn|n)(o|aṃ|a|ā|e)$", "", word)
        if len(base) >= 2:
            out.append(KitakaProposal(base, "-na", "past participle (pp)", "§556 Na"))

    # §561 Tuṃ, Tave: infinitives
    if word.endswith(("tuṃ", "tave", "tuye")):
        base = re.sub(r"(tuṃ|tave|tuye)$", "", word)
        out.append(KitakaProposal(base, "-tuṃ", "infinitive (inf)", "§561 Tuṃ"))

    # §563 Tvā, Tvāna, Tūna: absolutives / gerunds
    if word.endswith(("tvā", "tvāna", "tūna")):
        base = re.sub(r"(tvā|tvāna|tūna)$", "", word)
        out.append(KitakaProposal(base, "-tvā", "absolutive (abs)", "§563 Tvā"))

    # §622 Yu -> ana: action and state verbal nouns (gamana, dāna, vedanā)
    if word.endswith(("ana", "anaṃ", "anā")):
        base = re.sub(r"an(?:aṃ|a|ā)?$", "", word)
        out.append(KitakaProposal(base, "-ana", "action noun", "§622 Yu -> ana"))

    return out
