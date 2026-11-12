"""Pāṇinian rules from the *Aṣṭādhyāyī* for Sanskrit sandhi, samāsa, kṛdanta and taddhita analysis.

Alongside Kaccāyana's *Sandhikappa* (:mod:`kavi.sandhi`) and Edgerton's *Buddhist Hybrid Sanskrit Grammar*
(:mod:`kavi.bhs`), this module codifies Pāṇini's morphophonemic and derivational rules:

* **Ac-sandhi** (6.1.73–109): *yaṇ* (6.1.77 ``iko yaṇ aci``), *ayādi* and *y/v-lopa* (6.1.78 ``eco 'yavāyāvaḥ``,
  8.3.19 ``lopaḥ śākalyasya``), *guṇa* (6.1.87 ``ād guṇaḥ``), *vṛddhi* (6.1.88 ``vṛddhir eci``), *savarṇa-dīrgha*
  (6.1.101 ``akaḥ savarṇe dīrghaḥ``), and *tuk-āgama* before ``ch`` (6.1.73–76 ``che ca``, ``padāntād vā``);
* **Hal-sandhi** (8.2.30–8.4.63): *jaśtva* (8.2.39 ``jhalāṃ jaśo 'nte``), *ṅam-doubling* (8.3.32 ``ṅamo hrasvād aci
  ṅamuṇ nityam``), *ścutva* and *chatva* (8.4.40 ``stoḥ ścunā ścuḥ``, 8.4.63 ``śaś cho 'ṭi``), *ṣṭutva* (8.4.41
  ``ṣṭunā ṣṭuḥ``), *anunāsika* (8.4.45 ``yaro 'nunāsike 'nunāsiko vā``), *cartva* (8.4.55 ``khari ca``), *pararūpa*
  before ``l`` (8.4.60 ``tor li``), and voiced aspirate assimilation of ``h`` (8.4.62 ``jhayo ho 'nyatarasyām``);
* **Visarga and rutva sandhi** (6.1.113–114, 8.2.66 ``sasajuṣo ruḥ``, 8.3.14 ``ro ri``, 6.3.111 ``ḍhralope pūrvasya
  dīrgho 'ṇaḥ``, 8.3.34 ``visarjanīyasya saḥ``);
* **Internal retroflexion** across prefix and compound boundaries: *ṇatva* (8.4.1 ``raṣābhyāṃ no ṇaḥ samānapade``,
  8.4.2 ``aṭkupvāṅnumvyavāye 'pi``, 8.4.14 ``upasargād asamāse 'pi ṇopadeśasya``) and *ṣatva* (8.3.59
  ``ādeśapratyayayoḥ``);
* **Samāsa and taddhita formations**: *cvi* stems before ``kṛ``/``bhū`` (5.4.50 ``kṛbhvastiyoge sampadyakartari
  cviḥ``), *samāsānta* stem changes (5.4.68–154), initial *vṛddhi* in *taddhita* derivatives (7.2.117 ``taddhiteṣv
  acām ādeḥ``), and ``-tṛ`` agent nouns (3.1.133 ``ṇvul-tṛcau``, 4.1.5 ``ṛnnebhyo ṅīp`` vs 4.1.10 ``na ṣvasrādibhyaḥ``).

Also holds the attested Buddhist Sanskrit compound-member and lemma sets extracted from Śāntideva's
*Bodhicaryāvatāra* and Aśvaghoṣa's *Saundarananda* in the Digital Corpus of Sanskrit (``ambuda-org/dcs``, CC-BY 4.0).
"""

from __future__ import annotations

import re

VOWELS = "aāiīuūṛṝḷeo"
VOICED = "gjḍdbnmyrlvhñṅṇ"

# Pāṇini 8.4.2 aṭkupvāṅnumvyavāye 'pi: sounds that do not block ṇatva after r, ṣ, ṛ, ṝ
# aṭ (vowels + h, y, v, r), ku (k, kh, g, gh, ṅ), pu (p, ph, b, bh, m), āṅ, num (ṃ)
_NATVA_TRANSPARENT = set("aāiīuūṛṝḷeohyvrkgṅpbṃm")
_NATVA_TRIGGERS = set("rṣṛṝ")

# Pāṇini 4.1.10 na ṣvasrādibhyaḥ: kinship ṛ-stems (not -tṛc/-tṛn agent nouns of 3.1.133)
KINSHIP_R_STEMS = {"mātṛ", "svasṛ", "duhitṛ", "nanāndṛ", "yātṛ", "pitṛ", "bhrātṛ", "jāmātṛ", "devṛ", "naptṛ"}

# Pāṇini 5.4.68–154 samāsānta stem alternations at the end of a compound
SAMASANTA_STEMS = {
    "rāja": "rājan",     # 5.4.91 rājāhaskhibhyaṣ ṭac
    "sakha": "sakhi",    # 5.4.91
    "ahna": "ahan",      # 5.4.88 ahno 'hna etebhyaḥ
    "patha": "pathin",   # 5.4.74 ṛkpūrabdhūḥpathām ānakṣe
}

# Attested Buddhist Sanskrit compound prior members (count >= 4 in Bodhicaryāvatāra + Saundarananda, ambuda-org/dcs)
DCS_COMP_MEMBERS: set[str] = {
    "acala", "adhvan", "adhyātma", "agni", "ajita", "alpa", "amara", "amedhya", "amṛta", "ananta", "anartha",
    "anitya", "anya", "anyonya", "aprameya", "apsaras", "apāya", "ardha", "arjana", "artha", "asamprajanya",
    "asat", "asi", "asthi", "atyanta", "aṅga", "aśru", "aśuci", "aśva", "bahu", "bala", "bandh", "bhakti",
    "bhava", "bhaya", "bhaikṣa", "bhaiṣajya", "bhāryā", "bhāva", "bhū", "bodhi", "bodhisattva", "brahman",
    "buddha", "bāla", "bīja", "cal", "cala", "candana", "caryā", "chanda", "cheda", "cikitsā", "cintā", "cira",
    "citra", "citta", "danta", "dayā", "daśan", "deva", "dhana", "dharma", "dhyāna", "dhātu", "dhṛti", "diś",
    "doṣa", "durgati", "duḥkha", "dveṣa", "dvi", "dāsa", "dīrgha", "dṛś", "dṛṣṭi", "eka", "etad", "gam",
    "gandha", "garbha", "gati", "ghāta", "grahaṇa", "guru", "guṇa", "gṛha", "gūtha", "harmya", "hasta", "heman",
    "hetu", "hima", "hita", "hṛdaya", "icchā", "indriya", "jagant", "jala", "jan", "jana", "janman", "jarā",
    "jina", "jñā", "jñāna", "jīva", "jīvita", "kalpa", "kara", "karman", "karuṇā", "keśa", "klama", "kleśa",
    "kriyā", "krodha", "krīḍā", "kula", "kuśala", "kāla", "kāma", "kāntāra", "kārya", "kāvya", "kāya", "kāṣṭha",
    "kṛpā", "kṣamā", "kṣaya", "kṣaṇa", "kṣetra", "kṣudh", "loka", "lola", "lābha", "mad", "mada", "madana",
    "mahat", "maitra", "mala", "manas", "manuṣya", "maraṇa", "mati", "maṇi", "megha", "mitra", "moha", "mokṣa",
    "mukha", "muni", "māna", "mārga", "māyā", "māṃsa", "mṛd", "mṛdu", "mṛtyu", "nadī", "nagara", "nagarī", "naraka",
    "nidrā", "nitya", "niyam", "niyama", "niviś", "nāman", "nṛpa", "ogha", "padma", "pakṣa", "para", "parama",
    "paraspara", "parārtha", "parātman", "pattra", "paṭa", "phala", "pipāsā", "pitta", "pitṛ", "prajñā",
    "prakṛti", "pratyaya", "pratīkāra", "priya", "prīti", "puruṣa", "putra", "puṇya", "puṣpa", "pāda", "pāpa",
    "pātra", "piṇḍa", "piṇḍapāta", "cīvara", "vihāra", "ārāma", "vyākaraṇa", "pīna", "pūjā", "pūrva", "rajas", "rakta", "rakṣaṇa", "rakṣā", "rasa", "asthi", "ratha", "rati",
    "ratna", "rukma", "rūpa", "rāga", "rājan", "saddharma", "sakala", "sama", "sambodhi", "sarva", "sat",
    "satata", "satkāra", "sattva", "satya", "saṃsāra", "smṛti", "sneha", "sthira", "sthāna", "strī", "stuti",
    "sugata", "sukha", "sura", "suvarṇa", "sva", "svabhāva", "svapna", "svarga", "tad", "tala", "tamas", "tap",
    "tapas", "tattva", "tri", "trāṇa", "tuṣṭi", "tva", "tvad", "tyāga", "tṛṣṇā", "ubhaya", "ujjvala", "uttama",
    "uṣṇa", "vadha", "vaiḍūrya", "vajra", "vana", "vara", "veda", "vighāta", "vimokṣa", "vimāna",
    "viveka", "vividha", "viśeṣa", "viṣa", "viṣaya", "vrata", "vyasana", "vyathā", "vyādhi", "vāc", "vāsa",
    "vāta", "vāyu", "vṛkṣa", "yad", "yama", "yaśas", "yoga", "yuga", "yuj", "ādā", "ādi", "āhāra", "ākāśa",
    "ārdra", "ārta", "ārya", "āsana", "ātman", "āvṛ", "āyam", "ṛṣi", "śabda", "śākya", "śam", "śama", "śarīra",
    "śatru", "śayyā", "śīla", "śīta", "śoka", "śraddhā", "śrama", "śruta", "śruti", "śubha", "śūnya",
}

# Attested Buddhist Sanskrit high-frequency lemmas (count >= 10 in Bodhicaryāvatāra + Saundarananda, ambuda-org/dcs)
DCS_COMMON_LEMMAS: set[str] = {
    "abhāva", "abhyāsa", "adas", "adhigam", "adhika", "adya", "agni", "agra", "akṣa", "alpa", "ambhas",
    "amedhya", "amṛta", "anartha", "anitya", "anna", "anta", "antar", "antara", "anubhū", "anvita", "anya",
    "anyathā", "anyatra", "anyonya", "apara", "api", "aprameya", "apriya", "apsaras", "arh", "ari", "artha",
    "arthin", "arṇava", "asat", "atha", "atho", "ati", "atra", "atas", "avagam", "avasthā", "ave", "avekṣ",
    "avāp", "aṅga", "aṅganā", "aṇu", "aśru", "aśubha", "aśuci", "bahu", "bala", "bandh", "bandhana", "bandhu",
    "bhaj", "bhakti", "bhartṛ", "bhava", "bhaya", "bhid", "bhikṣu", "bhram", "bhraṃś", "bhrātṛ", "bhuj",
    "bhāryā", "bhāva", "bhāvay", "bhāṣ", "bhī", "bhṛ", "bhū", "bhūmi", "bhūyas", "bodhi", "bodhisattva", "brū",
    "buddha", "buddhi", "budh", "bādh", "bāhu", "bāla", "bāṣpa", "bīja", "cakṣus", "cal", "cala", "car",
    "caryā", "catur", "ced", "cetas", "chanda", "chid", "cintay", "cintā", "citra", "citta", "dah", "darśana",
    "dehin", "deva", "deśa", "dhairya", "dhana", "dharma", "dhyāna", "dhātu", "dhṛti", "div", "diś", "doṣa",
    "durbala", "durgati", "durlabha", "duḥkha", "duḥkhita", "duṣkara", "dveṣa", "dīrgha", "dṛś", "dṛṣṭi", "eka",
    "enad", "etad", "eva", "evam", "gam", "gandha", "garbha", "gati", "gaṇa", "grah", "guru", "guṇa", "guṇavat",
    "gṛha", "han", "hasta", "hetu", "hita", "hṛd", "hṛdaya", "icchā", "idam", "iha", "indriya", "iti", "iva",
    "jagant", "jala", "jan", "jana", "janay", "janman", "jarā", "jina", "jña", "jñā", "jñāna", "jāti", "jīvita",
    "kadā", "kalpa", "kara", "karman", "katham", "kathay", "kaścana", "kaścit", "khalu", "kila", "kleśa", "kopa",
    "kriyā", "krodha", "kula", "kup", "kutas", "kuśala", "kva", "kvacid", "kāla", "kāma", "kāraṇa", "kārin",
    "kārya", "kāya", "kāṣṭha", "kṛpā", "kṣama", "kṣamā", "kṣaya", "kṣaṇa", "kṣetra", "kṣip", "labh", "loka",
    "lola", "lābha", "mad", "mada", "madhya", "mahat", "maitrī", "man", "manas", "manuṣya", "maraṇa", "mati",
    "maya", "megha", "mitra", "moha", "mokṣa", "muc", "muh", "muhur", "mukha", "muni", "māna", "mānasa",
    "mārga", "mātra", "māyā", "māṃsa", "mūla", "mūrdhan", "mṛdu", "mṛtyu", "nadī", "nam", "nanda", "nanu",
    "nagara", "nagarī", "nara", "naraka", "naś", "nidrā", "nigrah", "nihan", "nimitta", "nitya", "nityam", "nivāray", "nivṛt",
    "niyama", "niyatam", "niścaya", "niśāmay", "nāma", "nāraka", "nātha", "nṛpa", "pada", "padma", "pakṣa",
    "para", "parama", "paraspara", "parigraha", "parārtha", "pat", "pathin", "paś", "phala", "pitṛ", "prabhṛti",
    "prajñā", "prajā", "prakṛti", "prasāda", "prasū", "prati", "pratyaya", "pravṛt", "pravṛtti", "praviś",
    "prayoga", "prayā", "praśama", "praṇam", "priya", "priyā", "prāp", "prīti", "punar", "pura", "puruṣa",
    "putra", "puṇya", "puṣpa", "pāda", "pāpa", "pātra", "piṇḍa", "piṇḍapāta", "cīvara", "vihāra", "ārāma", "vyākaraṇa", "pūjay", "pūjā", "pūrva", "pūrvam", "rajas", "rakṣ",
    "ram", "rasa", "asthi", "ratha", "rati", "ratna", "ripu", "roga", "rūpa", "rāga", "rājan", "saddharma",
    "sadā", "sadṛśa", "saha", "sama", "sambhava", "sampad", "samyak", "sarva", "sarvatra", "sat", "satatam",
    "sattva", "satya", "saukhya", "saumya", "saṃjñā", "saṃsāra", "saṃvṛti", "sañj", "sev", "sidh", "siddhi",
    "smṛ", "smṛti", "sneha", "stha", "sthira", "sthā", "sthāna", "strī", "sugata", "suhṛd", "sukha", "sukhin",
    "suta", "suvarṇa", "sva", "svabhāva", "svap", "svapna", "svarga", "svastha", "svayam", "sādhu", "sāra",
    "sūkṣma", "tad", "tadvat", "tadā", "tala", "tamas", "tanu", "tapas", "tarṣa", "tasmāt", "tatas", "tathā",
    "tathāgata", "tatra", "tattva", "tri", "trāsa", "trāṇa", "tvad", "tva", "tyaj", "tāvat", "tīvra", "tṛpti",
    "tṛṣṇā", "udi", "upama", "upapad", "upe", "utpad", "uttama", "utthā", "vac", "vacas", "vad", "vadha", "vah",
    "vana", "vapus", "vara", "vastu", "vat", "vaśa", "vedanā", "vibhūṣaṇa", "vicintay", "vicāra", "vicāray",
    "vid", "vidhi", "vidhā", "vihā", "vihṛ", "vimokṣa", "vimuc", "vinā", "viveka", "vividha", "viśeṣa",
    "viśeṣaka", "viṣa", "viṣaya", "vrata", "vyasana", "vyathā", "vyādhi", "vāc", "vākya", "vāray", "vāsas",
    "vāyu", "vīrya", "vṛdh", "vṛddhi", "vṛkṣa", "vṛt", "yad", "yadi", "yadā", "yasmāt", "yat", "yatas", "yathā",
    "yatna", "yatra", "yauvana", "yaśas", "yoga", "yogin", "yuj", "yāvat", "ādā", "ādi", "āgam", "āgama",
    "āhāra", "ākāśa", "ākṣip", "āpad", "ārabh", "ārya", "āsana", "āsthā", "āśaya", "āśraya", "āśri", "ātmaka",
    "ātman", "āyus", "īdṛśa", "īkṣ", "ṛṣi", "śabda", "śak", "śam", "śama", "śaraṇa", "śarīra", "śastra", "śata",
    "śatru", "śiva", "śikṣā", "śīla", "śoka", "śraddhā", "śrama", "śreyas", "śrī", "śru", "śubha", "śuc",
    "śuci", "śānti", "śūnya", "śūnyatā",
}


def is_agent_tr(stem: str) -> bool:
    """Pāṇini 3.1.133 ``ṇvul-tṛcau`` & 4.1.5 ``ṛnnebhyo ṅīp`` vs 4.1.10 ``na ṣvasrādibhyaḥ``:
    whether ``stem`` is an agent noun in ``-tṛ`` (masculine/adjective; feminine is ``-trī``), not a kinship noun."""
    return stem.endswith("tṛ") and len(stem) >= 4 and stem not in KINSHIP_R_STEMS


def triggers_natva(left: str) -> bool:
    """Pāṇini 8.4.1 ``raṣābhyāṃ no ṇaḥ samānapade`` & 8.4.2 ``aṭkupvāṅnumvyavāye 'pi``:
    whether ``left`` ends with a ``r/ṣ/ṛ/ṝ`` trigger followed only by *aṭ-ku-pu-āṅ-num* sounds."""
    for idx in range(len(left) - 1, -1, -1):
        ch = left[idx]
        if ch in _NATVA_TRIGGERS:
            return True
        if ch not in _NATVA_TRANSPARENT:
            return False
    return False


def undo_natva(left: str, right: str) -> list[str]:
    """Pāṇini 8.4.1–14: restore ``ṇ -> n`` in ``right`` when triggered by ``r/ṣ/ṛ/ṝ`` in ``left``
    (``pra + ṇidhi -> pra + nidhi``, ``pari + ṇāma -> pari + nāma``, ``nir + ṇimitta -> nir + nimitta``,
    ``pūrva + ahṇa -> pūrva + ahna``)."""
    if not right or "ṇ" not in right or not triggers_natva(left):
        return []
    out: list[str] = []
    if right.startswith("ṇ"):
        out.append("n" + right[1:])
    for i, ch in enumerate(right):
        if ch == "ṇ" and i > 0:
            out.append(right[:i] + "n" + right[i + 1:])
            break
        if ch not in _NATVA_TRANSPARENT:
            break
    return out


def undo_satva(left: str, right: str) -> list[str]:
    """Pāṇini 8.3.59 ``ādeśapratyayayoḥ`` + 8.4.41 ``ṣṭunā ṣṭuḥ``: after *iṇ* (``i/u/ṛ/e/o/r/k``) in ``left``,
    restore initial ``ṣ- -> s-``, ``ṣṭ- -> st-``, ``ṣṭh- -> sth-``, ``ṣṇ- -> sn-`` in ``right``
    (``prati + ṣṭhita -> prati + sthita``, ``anu + ṣṭhāna -> anu + sthāna``, ``abhi + ṣeka -> abhi + seka``)."""
    if not left or not right or left[-1] not in "iīuūṛṝeorḥṣk":
        return []
    if right.startswith("ṣṭh"):
        return ["sth" + right[3:]]
    if right.startswith("ṣṭ"):
        return ["st" + right[2:]]
    if right.startswith("ṣṇ"):
        return ["sn" + right[2:]]
    if right.startswith("ṣ"):
        return ["s" + right[1:]]
    return []


def undo_initial_vrddhi(stem: str) -> list[str]:
    """Pāṇini 7.2.117 ``taddhiteṣv acām ādeḥ``: undo initial *vṛddhi* (``ā -> a``, ``ai -> i/e``, ``au -> u/o``,
    ``ār -> ar/ṛ``) to recover the base *prātipadika* of a *taddhita* derivative (``laukika -> loka``,
    ``dhārmika -> dharma``, ``kārṣṇa -> kṛṣṇa``, ``vaiśāradya -> viśārada``, ``daurmanasya -> durmanas``,
    ``ādhyātmika -> adhyātma``); 7.3.3 ``na yvābhyāṃ padāntābhyāṃ pūrvau tu tābhyām aic``: after the ``y`` or ``v`` of a
    prefix the vowel is not strengthened, ``ai``/``au`` is put before the semivowel instead (``naiyāyika -> nyāya``,
    ``vaiyākaraṇa -> vyākaraṇa``, ``sauvastika -> svasti``)."""
    out: list[str] = []
    # Match optional initial consonant cluster before the first vowel
    m = re.match(r"^([^aāiīuūṛṝḷeo]*)(ai|au|ār|ā)(.+)$", stem)
    if not m:
        return out
    ons, v, rest = m.group(1), m.group(2), m.group(3)
    if v == "ā":
        out.append(ons + "a" + rest)
    elif v == "ai":
        out.append(ons + "i" + rest)
        out.append(ons + "e" + rest)
        if ons and rest.startswith("y"):                             # 7.3.3 naiyāyika -> nyāya, vaiyākaraṇa -> vyākaraṇa
            out.append(ons + rest)
    elif v == "au":
        out.append(ons + "u" + rest)
        out.append(ons + "o" + rest)
        if ons and rest.startswith("v"):                             # 7.3.3 sauvastika -> svasti, dauvārika -> dvāra
            out.append(ons + rest)
    elif v == "ār":
        out.append(ons + "ar" + rest)                                # ā -> a before r (dhārmika -> dharma), the commoner case
        out.append(ons + "ṛ" + rest)                                 # ār -> ṛ (kārṣṇa -> kṛṣṇa)
    return out


def compound_junction_variants(left: str, right: str) -> list[tuple[str, str]]:
    """Pāṇinian morphophonemic reversals at a compound or prefix boundary ``(left, right)``."""
    out = [(left, right)]
    vowel = right[:1] in VOWELS
    # 6.1.101 akaḥ savarṇe dīrghaḥ & 6.3.137 anyeṣām api dṛśyate (lengthening of final vowel in prior compound member)
    if left.endswith("ā"):
        out += [(left[:-1] + "a", "ā" + right), (left[:-1] + "a", "a" + right), (left, "a" + right)]
        if not vowel and len(left) >= 4 and right.startswith(("rāj", "mitr")):
            out += [(left[:-1] + "a", right)]                        # 6.3.137 viśvāmitra, rāṣṭrārājadhānī
    if left.endswith("ī"):
        out += [(left[:-1] + "i", "i" + right), (left[:-1] + "i", "ī" + right)]
        if not vowel and len(left) >= 4:
            out += [(left[:-1] + "i", right)]                        # 6.3.137 koṭīniyuta -> koṭi + niyuta
    if left.endswith("ū"):
        out += [(left[:-1] + "u", "u" + right), (left[:-1] + "u", "ū" + right)]
        if not vowel and len(left) >= 4:
            out += [(left[:-1] + "u", right)]
    # 6.1.87 ād guṇaḥ (a/ā + i/ī -> e; a/ā + u/ū -> o; a/ā + ṛ -> ar)
    if left.endswith("e"):
        out += [(left[:-1] + "a", "i" + right), (left[:-1] + "a", "ī" + right), (left[:-1] + "ā", "i" + right)]
    if left.endswith("o"):
        out += [(left[:-1] + "a", "u" + right), (left[:-1] + "a", "ū" + right), (left[:-1] + "ā", "u" + right),
                (left[:-1] + "aḥ", right), (left[:-1] + "as", right)]   # 6.1.114 haśi ca (manas + ratha -> manoratha)
    if left.endswith("ar") and len(left) >= 3:
        out += [(left[:-2] + "a", "ṛ" + right), (left[:-2] + "ā", "ṛ" + right)]   # maharṣi -> mahā + ṛṣi, saptarṣi -> sapta + ṛṣi
    # 6.1.88 vṛddhir eci (a/ā + e/ai -> ai; a/ā + o/au -> au)
    if left.endswith("ai") and len(left) >= 3:
        out += [(left[:-2] + "a", "e" + right), (left[:-2] + "ā", "e" + right), (left[:-2] + "a", "ai" + right)]
    if left.endswith("au") and len(left) >= 3:
        out += [(left[:-2] + "a", "o" + right), (left[:-2] + "ā", "o" + right), (left[:-2] + "a", "au" + right)]
    # 8.2.7 nalopaḥ prātipadikāntasya (an-stem drops final n in prior compound member: ātma-, nāma-, karma-, brahma-)
    if left.endswith("a") and len(left) >= 3:
        out += [(left + "n", right)]
    # 6.1.77 iko yaṇ aci (i/ī -> y, u/ū -> v, ṛ -> r before dissimilar vowel)
    if left.endswith("y") and vowel:
        out += [(left[:-1] + "i", right), (left[:-1] + "ī", right)]
    if left.endswith("v") and vowel:
        out += [(left[:-1] + "u", right), (left[:-1] + "ū", right)]
    if left.endswith("r") and vowel and len(left) >= 3 and left[-2] in "ptkbdgmnśṣshv":
        out += [(left[:-1] + "ṛ", right)]                            # pitrartha -> pitṛ + artha, mātrartha -> mātṛ + artha
    # 8.2.66 sasajuṣo ruḥ & 8.3.34 visarjanīyasya saḥ
    if left.endswith(("ś", "ṣ", "s", "r")):
        out += [(left[:-1] + "ḥ", right), (left[:-1] + "s", right)]
    # 8.3.14 ro ri & 6.3.111 ḍhralope pūrvasya dīrgho 'ṇaḥ (nīroga -> niḥ + roga, nīrasa -> niḥ + rasa)
    if right.startswith("r") and len(left) >= 2 and left[-1] in "āīū":
        short = {"ā": "a", "ī": "i", "ū": "u"}[left[-1]]
        out += [(left[:-1] + short + "ḥ", right), (left[:-1] + short + "r", right)]
    # 8.2.30 coḥ kuḥ & 8.2.39 jhalāṃ jaśo 'nte
    if left.endswith("d"):
        out += [(left[:-1] + "t", right)]
    if left.endswith("g"):
        out += [(left[:-1] + "k", right), (left[:-1] + "c", right)]
    if left.endswith("ḍ"):
        out += [(left[:-1] + "ṭ", right), (left[:-1] + "ṣ", right)]   # ṣaḍāyatana -> ṣaṭ/ṣaṣ + āyatana
    if left.endswith("b"):
        out += [(left[:-1] + "p", right)]                            # abdhātu -> ap + dhātu
    if left.endswith("j") and right[:1] in "jñ":
        out += [(left[:-1] + "t", right), (left[:-1] + "d", right)]  # tajjñāna -> tat + jñāna
    if left.endswith("c") and right[:1] in "cś":
        out += [(left[:-1] + "t", right), (left[:-1] + "d", right)]  # saccit -> sat + cit
    # 8.3.23 mo 'nusvāraḥ & 8.4.45 yaro 'nunāsike 'nunāsiko vā
    if left.endswith("ṃ"):
        out += [(left[:-1] + "m", right)]
    if left.endswith("n") and right[:1] in "mn" and len(left) >= 3:
        out += [(left[:-1] + "t", right)]                            # tanmaya -> tat + maya, jagannātha -> jagat + nātha
    if left.endswith("ṅ") and right[:1] in "mn" and len(left) >= 3:
        out += [(left[:-1] + "k", right), (left[:-1] + "c", right)]  # vāṅmaya -> vāc + maya, diṅnāga -> diś/dik + nāga
    if left.endswith("ṇ") and right[:1] in "mn" and len(left) >= 2:
        out += [(left[:-1] + "ṭ", right), (left[:-1] + "ṣ", right)]  # ṣaṇmukha -> ṣaṭ/ṣaṣ + mukha
    if left.endswith("m") and right[:1] in "mn" and len(left) >= 2:
        out += [(left[:-1] + "p", right)]                            # ammaya -> ap + maya
    # 8.4.60 tor li (tallaya -> tat + laya)
    if left.endswith("l") and right.startswith("l") and len(left) >= 3:
        out += [(left[:-1] + "t", right), (left[:-1] + "d", right)]
    # 8.4.62 jhayo ho 'nyatarasyām (taddhita -> tat + hita, uddharaṇa -> ud + haraṇa)
    if left.endswith("d") and right.startswith("dh"):
        out += [(left[:-1] + "t", "h" + right[2:]), (left, "h" + right[2:])]
    if left.endswith("g") and right.startswith("gh"):
        out += [(left[:-1] + "k", "h" + right[2:]), (left[:-1] + "c", "h" + right[2:])]
    # 5.4.50 kṛbhvastiyoge sampadyakartari cviḥ (ekībhūta -> eka + bhūta, śūnyīkṛta -> śūnya + kṛta)
    if left.endswith("ī") and right.startswith(("kṛ", "bhū", "kar", "bhav")) and len(left) >= 3:
        out += [(left[:-1] + "a", right), (left[:-1] + "i", right)]
    if left.endswith("ū") and right.startswith(("kṛ", "bhū", "kar", "bhav")) and len(left) >= 3:
        out += [(left[:-1] + "u", right)]
    # 6.1.73–76 che ca / padāntād vā & 8.4.63 śaś cho 'ṭi
    if right.startswith("ch"):
        out += [(left, "ś" + right[2:])]
        if left.endswith("c"):
            out += [(left[:-1] + "t", "ś" + right[2:]), (left[:-1] + "t", right), (left[:-1], right)]   # svacchanda -> sva + chanda
    # 8.3.59 ādeśapratyayayoḥ (ṣatva) & 8.4.1 raṣābhyāṃ no ṇaḥ samānapade (ṇatva)
    for r_satva in undo_satva(left, right):
        out.append((left, r_satva))
    for r_natva in undo_natva(left, right):
        out.append((left, r_natva))
    return out


def external_sandhi_cands(key: str, i: int) -> list[tuple[str, str]]:
    """Pāṇinian reverse *saṃhitā* candidates at index ``i`` of ``key``."""
    ch = key[i]
    pair = key[i:i + 2]
    cands: list[tuple[str, str]] = []
    # 6.1.88 vṛddhir eci
    if pair == "ai":
        cands += [(key[:i] + "a", "e" + key[i + 2:]), (key[:i] + "ā", "e" + key[i + 2:]), (key[:i] + "a", "ai" + key[i + 2:])]
    elif pair == "au":
        cands += [(key[:i] + "a", "o" + key[i + 2:]), (key[:i] + "ā", "o" + key[i + 2:]), (key[:i] + "a", "au" + key[i + 2:])]
    # 6.1.101 akaḥ savarṇe dīrghaḥ & 8.3.14 ro ri + 6.3.111 ḍhralope pūrvasya dīrgho 'ṇaḥ
    elif ch == "ā":
        cands += [(key[:i] + "a", "a" + key[i + 1:]), (key[:i] + "ā", "a" + key[i + 1:]),
                  (key[:i] + "a", "ā" + key[i + 1:]), (key[:i] + "ā", "ā" + key[i + 1:])]
        if key[i + 1:i + 2] == "r":
            cands += [(key[:i] + "ar", key[i + 1:]), (key[:i] + "aḥ", key[i + 1:])]   # punāramate -> punar + ramate
    elif ch == "e":
        # 6.1.87 ād guṇaḥ
        cands += [(key[:i] + "a", "i" + key[i + 1:]), (key[:i] + "ā", "i" + key[i + 1:]),
                  (key[:i] + "a", "ī" + key[i + 1:]), (key[:i] + "a", "e" + key[i + 1:])]
    elif ch == "o":
        # 6.1.87 ād guṇaḥ & 6.1.113–114 ato ror aplutād aplute / haśi ca
        cands += [(key[:i] + "a", "u" + key[i + 1:]), (key[:i] + "ā", "u" + key[i + 1:]),
                  (key[:i] + "aḥ", "a" + key[i + 1:]), (key[:i] + "a", "o" + key[i + 1:]),
                  (key[:i] + "a", "ū" + key[i + 1:]), (key[:i] + "ā", "ū" + key[i + 1:])]
        if key[i + 1:i + 2] in VOICED:
            cands += [(key[:i] + "aḥ", key[i + 1:])]                 # tejodhātur, manodharmaḥ, bhikṣavo भगवन्
    elif ch == "ī":
        cands += [(key[:i] + "i", "i" + key[i + 1:]), (key[:i] + "ī", "i" + key[i + 1:]), (key[:i] + "i", "ī" + key[i + 1:])]
        if key[i + 1:i + 2] == "r":
            cands += [(key[:i] + "iḥ", key[i + 1:]), (key[:i] + "ir", key[i + 1:])]   # 8.3.14 + 6.3.111
    elif ch == "ū":
        cands += [(key[:i] + "u", "u" + key[i + 1:]), (key[:i] + "u", "ū" + key[i + 1:])]
        if key[i + 1:i + 2] == "r":
            cands += [(key[:i] + "uḥ", key[i + 1:]), (key[:i] + "ur", key[i + 1:])]
    # 8.3.34 visarjanīyasya saḥ (+ 8.4.40/41)
    elif ch == "s" and i >= 2 and key[i + 1] in "tṭc":
        cands += [(key[:i] + "ḥ", key[i + 1:])]
    elif ch == "ś" and i >= 2 and key[i + 1] in "cś":
        cands += [(key[:i] + "ḥ", key[i + 1:])]
    elif ch == "ṣ" and i >= 2 and key[i + 1] in "ṭkṣp":
        cands += [(key[:i] + "ḥ", key[i + 1:])]
    # 8.3.36 vā śari & 8.3.37 kupvoḥ ḥkḥpau ca (visarga unchanged before sibilants and voiceless velars/labials: antaḥ + śauṣiryam)
    elif ch == "ḥ" and i >= 2 and key[i + 1:i + 2] in "śṣskp":
        cands += [(key[:i + 1], key[i + 1:])]
    # 8.4.40 stoḥ ścunā ścuḥ & 8.4.63 śaś cho 'ṭi & 6.1.73 che ca
    elif pair == "cc" and i >= 2:
        rest = key[i + 1:]
        if rest.startswith("ch"):
            cands += [(key[:i] + "t", "ś" + rest[2:]), (key[:i] + "t", rest)]
        elif rest[1:2] in VOWELS:
            cands += [(key[:i] + "t", rest)]
    elif pair == "jj" and i >= 2:
        cands += [(key[:i] + "t", key[i + 1:])]
    # 8.2.39 jhalāṃ jaśo 'nte & 8.4.62 jhayo ho 'nyatarasyām
    elif pair == "dd" and i >= 2:
        rest = key[i + 1:]
        cands += [(key[:i] + "t", rest)]
        if rest.startswith("dh"):
            cands += [(key[:i] + "t", "h" + rest[2:])]
    # 8.4.45 yaro 'nunāsike 'nunāsiko vā & 8.3.32 ṅamo hrasvād aci ṅamuṇ nityam
    elif pair in ("nn", "nm") and i >= 2:
        cands += [(key[:i] + "t", key[i + 1:]), (key[:i] + "n", key[i + 1:])]
    elif pair in ("ṅm", "ṅn") and i >= 2:
        cands += [(key[:i] + "k", key[i + 1:]), (key[:i] + "c", key[i + 1:])]
    elif pair in ("ṇm", "ṇn") and i >= 2:
        cands += [(key[:i] + "ṭ", key[i + 1:])]
    # 8.4.60 tor li
    elif pair == "ll" and i >= 2:
        cands += [(key[:i] + "n", key[i + 1:]), (key[:i] + "t", key[i + 1:])]
    elif ch == "ṃ" and i >= 2 and key[i + 1:i + 3] in ("st", "śc", "ṣṭ"):
        cands += [(key[:i] + "n", key[i + 2:])]
    elif ch == "ṃ" and i >= 2 and key[i + 1:i + 2] == "l":
        cands += [(key[:i] + "n", key[i + 1:]), (key[:i] + "m", key[i + 1:])]
    elif ch == "ñ" and i >= 2 and key[i + 1] in "jcś":
        cands += [(key[:i] + "n", key[i + 1:])]
        if key[i + 1:i + 3] == "ch":
            cands += [(key[:i] + "n", "ś" + key[i + 3:])]
    # 8.2.66 sasajuṣo ruḥ & 6.1.87 ād guṇaḥ (a/ā + ṛ -> ar)
    elif ch == "r" and i >= 2 and key[i + 1] in VOICED:
        rest = key[i + 1:]
        if key[i - 1] in "iīuūeoṛ" or key[i - 2:i] == "ai" or key[i - 2:i] == "au":
            cands += [(key[:i] + "ḥ", rest)]
        if key[i - 1] == "a":
            cands += [(key[:i] + "r", rest)]
            cands += [(key[:i], "ṛ" + rest), (key[:i - 1] + "ā", "ṛ" + rest)]
    # 8.2.39 jhalāṃ jaśo 'nte before voiced consonants or vowels
    elif ch == "g" and i >= 2 and (key[i + 1] in VOICED or key[i + 1] in VOWELS):
        cands += [(key[:i] + "k", key[i + 1:])]
    elif ch == "ḍ" and i >= 2 and (key[i + 1] in VOICED or key[i + 1] in VOWELS):
        cands += [(key[:i] + "ṭ", key[i + 1:])]
    elif ch == "b" and i >= 2 and (key[i + 1] in VOICED or key[i + 1] in VOWELS):
        cands += [(key[:i] + "p", key[i + 1:])]
    elif ch == "d" and i >= 2 and key[i + 1] in "gbdjvyrlmn":
        cands += [(key[:i] + "t", key[i + 1:]), (key[:i] + "d", key[i + 1:])]   # samavāyād bāhyasya, tasmād vyavahāraḥ
    elif ch in "mrydvn" and i >= 1 and key[i + 1] in VOWELS:
        rest = key[i + 1:]
        if ch == "m":
            cands += [(key[:i] + "m", rest)]
        elif ch == "r":
            if key[i - 1] in "iīuūeoṛ" or key[i - 2:i] in ("ai", "au"):
                cands += [(key[:i] + "ḥ", rest)]
            if key[i - 1] == "a":
                cands += [(key[:i] + "r", rest)]
        elif ch == "y":
            if key[i - 1] not in VOWELS:
                cands += [(key[:i] + "i", rest), (key[:i] + "ī", rest)]
            if key[i - 1] == "ā":
                cands += [(key[:i - 1] + "ai", rest)]
        elif ch == "v":
            if key[i - 1] not in VOWELS:
                cands += [(key[:i] + "u", rest), (key[:i] + "ū", rest)]
            if key[i - 1] == "ā":
                cands += [(key[:i - 1] + "au", rest)]
        elif ch == "d":
            cands += [(key[:i] + "t", rest), (key[:i] + "d", rest)]
        elif key[i - 1] == "n":
            cands += [(key[:i], rest), (key[:i] + "n", rest)]
        else:
            cands += [(key[:i] + "n", rest)]
    return cands
