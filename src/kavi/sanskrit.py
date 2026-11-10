"""Sanskrit and Buddhist Hybrid Sanskrit: word analysis behind the same interface as :class:`kavi.dpd.DPD`.

Morphology comes from vidyut's kosha (ambuda-org, MIT): every pada it knows carries its stem, gender, case and
number, or its root, tense, person and number. Meanings come from the Cologne dictionaries in ``sanskrit.sqlite``
(Edgerton's Buddhist Hybrid Sanskrit Dictionary first, then Monier-Williams, then Apte). A form the kosha lacks is
read, in turn, as a hybrid spelling (:mod:`kavi.bhs`), as a regular inflection of a stem the dictionaries know (the
ending identified on a model stem), as a compound of known members, or as two words joined by sandhi.

The lemmas follow the author's interlinear convention: a noun by its stem (``bodhisattva``, ``tad``), a verb by its
third person singular present (``viharati``), a participle by its own stem (``utpanna``) with the verb it belongs to
("pp of utpadyate"), a compound by its members (``prajñā + pāramitā + caryā``).
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import replace
from pathlib import Path

from .bhs import readings
from .cologne import Cologne, nasal_variants
from .dpd import Analysis, Headword, Split
from .panini import (
    DCS_COMMON_LEMMAS,
    DCS_COMP_MEMBERS,
    SAMASANTA_STEMS,
    compound_junction_variants,
    external_sandhi_cands,
    is_agent_tr,
    undo_initial_vrddhi,
    undo_natva,
    undo_satva,
)

try:
    from vidyut import lipi
    from vidyut.kosha import Kosha
    from vidyut.prakriya import Krt, Lakara, Pada, Pratipadika, Prayoga, Purusha, Vacana, Vyakarana
    HAVE_VIDYUT = True
except ImportError:                                            # pragma: no cover
    HAVE_VIDYUT = False

LANGUAGE = "Sanskrit"
CODE = "sa"
PUNCT = "‘’“”\"'.,;:?!()[]{}|*_`«»‹›=+/\\।॥"

# Kaccāyana's sabbanāma, in Sanskrit: the words that take the pronoun mark
PRONOUNS = {"tad", "etad", "idam", "adas", "yad", "kim", "sarva", "anya", "anyatara", "itara", "para", "apara", "pūrva",
            "dakṣiṇa", "uttara", "adhara", "ubha", "ubhaya", "eka", "katara", "katama", "sva", "aham", "tvam", "asmad", "yuṣmad",
            "ena", "tva", "nema", "sama", "sima", "viśva"}
LEMMA_SHOWN = {"asmad": "aham", "yuṣmad": "tvam"}

# Edgerton's and Monier-Williams' grammatical labels -> the DPD's part-of-speech abbreviations
LINGA = {"puM": "masc", "strI": "fem", "napuMsaka": "nt", "Pum": "masc", "Stri": "fem", "Napumsaka": "nt"}
VIBHAKTI = {"praTamA": "nom", "dvitIyA": "acc", "tftIyA": "instr", "caturTI": "dat", "paYcamI": "abl", "zazWI": "gen",
            "saptamI": "loc", "samboDanam": "voc", "Prathama": "nom", "Dvitiya": "acc", "Trtiya": "instr", "Caturthi": "dat",
            "Panchami": "abl", "Sasthi": "gen", "Saptami": "loc", "Sambodhana": "voc"}
VACANA = {"eka": "sg", "dvi": "dual", "bahu": "pl", "Eka": "sg", "Dvi": "dual", "Bahu": "pl"}
PURUSHA = {"praTama": "3rd", "maDyama": "2nd", "uttama": "1st", "Prathama": "3rd", "Madhyama": "2nd", "Uttama": "1st"}
LAKARA = {"la~w": "pr", "la~N": "imperf", "li~w": "perf", "lu~w": "pfut", "lf~w": "fut", "lo~w": "imp", "viDili~N": "opt",
          "ASIrli~N": "bened", "lu~N": "aor", "lf~N": "cond", "Lat": "pr", "Lan": "imperf", "Lit": "perf", "Lut": "pfut",
          "Lrt": "fut", "Lot": "imp", "VidhiLin": "opt", "AshirLin": "bened", "Lun": "aor", "Lrn": "cond"}
PRAYOGA_PASS = {"karmaRi", "BAve", "Karmani", "Bhave"}
# kṛt affixes -> (part of speech, the affix as the textbook writes it)
KRT = {"kta": ("pp", "ta"), "ktavatu~": ("pp", "tavat"), "Satf~": ("prp", "at"), "SAnac": ("prp", "māna"), "cAnaS": ("prp", "māna"),
       "tavya": ("ptp", "tavya"), "tavyat": ("ptp", "tavya"), "anIyar": ("ptp", "anīya"), "yat": ("ptp", "ya"), "Ryat": ("ptp", "ya"),
       "kyap": ("ptp", "ya"), "ktvA": ("abs", "tvā"), "lyap": ("abs", "ya"), "tumun": ("inf", "tum"), "Rvul": ("masc", "aka"),
       "tfc": ("masc", "tṛ"), "tfn": ("masc", "tṛ"), "lyu~w": ("nt", "ana"), "GaY": ("masc", "a"), "ktin": ("fem", "ti"), "Rini~": ("masc", "in"),
       "ac": ("masc", "a"), "ka": ("masc", "a"), "kvip": ("masc", ""), "kvi~p": ("masc", ""), "kvi~n": ("masc", ""),
       "tumu~n": ("inf", "tum"), "kvasu~": ("pp", "vas"), "kAnac": ("pp", "āna"), "SAnan": ("prp", "āna"), "Ramu~l": ("abs", "am"),
       "kamu~l": ("abs", "am"), "Rvu~l": ("masc", "aka"), "Rvu~c": ("masc", "aka"), "lyu~": ("nt", "ana"), "Yyu~w": ("nt", "ana"),
       "Ryu~w": ("nt", "ana"), "Ga": ("masc", "a"), "ki": ("masc", "i"), "kin": ("masc", "i"), "ktic": ("fem", "ti"), "ktri": ("nt", "tra"),
       "ini~": ("masc", "in"), "in": ("masc", "in"), "Ginu~R": ("masc", "in"), "mani~n": ("masc", "man"), "kasu~n": ("nt", "as"),
       "aTuc": ("masc", "athu"), "itra": ("nt", "itra"), "Uka": ("adj", "ūka"), "uka": ("adj", "uka"), "izRuc": ("adj", "iṣṇu")}
ATMANEPADA_ENDS = ("nte", "te", "se", "dhve", "mahe", "vahe", "āte", "āthe", "ete", "ethe", "ntām", "sva", "dhvam", "anta",
                   "thāḥ", "mahi", "vahi", "eran", "ethāḥ", "ṣṭa", "ṣīran", "īran", "āvahai", "āmahai", "ai")
# model stems for the regular inflections, by final sound and gender (vidyut knows every form of these)
MODELS = {("a", "masc"): "deva", ("a", "nt"): "phala", ("ā", "fem"): "mālā", ("i", "masc"): "agni", ("i", "fem"): "mati",
          ("i", "nt"): "vāri", ("u", "masc"): "guru", ("u", "nt"): "madhu", ("ī", "fem"): "nadī", ("ū", "fem"): "vadhū",
          ("ṛ", "masc"): "kartṛ", ("in", "masc"): "yogin", ("an", "masc"): "rājan", ("an", "nt"): "nāman",
          ("as", "nt"): "manas", ("vat", "masc"): "bhagavat", ("mat", "masc"): "dhīmat", ("at", "masc"): "bhavat",
          ("a", "pron"): "sarva", ("an", "num"): "pañcan"}
COMMON = {"ca", "na", "eva", "iti", "hi", "tu", "vā", "api", "sma", "atha", "khalu", "punar", "tatra", "iha", "tadā", "evam", "tathā",
          "yathā", "kim", "tad", "etad", "idam", "yad", "sa", "saḥ", "te", "me", "mama", "tvam", "aham", "yena", "tena", "yāvat", "tāvat",
          "kiṃ", "nu", "kho", "bhoḥ", "bho", "iva", "cet", "yadi", "tarhi", "tasmāt", "yasmāt", "katham", "kutra", "atra", "ity"}
# particles and adverbs the kosha knows only as inflected pronouns (tasmāt is tad in the ablative): read as indeclinables first
INDECLINABLES = {"tasmāt": "therefore", "yasmāt": "because", "tadyathā": "as follows", "evam": "thus", "iha": "here", "yāvat": "as far as, up to",
                 "tāvat": "so far", "pṛthak": "apart", "sma": "(past)", "svāhā": "hail", "iti": "thus", "atha": "then", "khalu": "indeed",
                 "punar": "again", "eva": "just", "api": "also", "ca": "and", "na": "not", "vā": "or", "hi": "for", "tu": "but", "tatra": "there",
                 "tataḥ": "then", "tathā": "so", "yathā": "as", "bhoḥ": "sir", "bho": "sir", "kutaḥ": "whence", "kva": "where", "nu": "now",
                 "kila": "indeed", "sadā": "always", "tadā": "then", "yadā": "when", "idānīm": "now", "adya": "today", "evaṃ": "thus",
                 "sārdham": "together with", "sacet": "if", "saced": "if", "cet": "if", "ced": "if", "saha": "with", "sākam": "together with", "paścāt": "afterwards",
                 "bhūyas": "further", "yathāpi": "just as", "itas": "from this, hence", "svatas": "from itself", "paratas": "from another",
                 "ubhayatas": "from both", "anyatas": "from elsewhere", "sarvatas": "from all sides", "ahetutas": "without a primary cause",
                 "ekatas": "from one side", "yatas": "whence, since", "atas": "hence", "tridhā": "in three ways", "dvidhā": "in two ways",
                 "caturdhā": "in four ways", "bahudhā": "in many ways", "anekadhā": "in many ways", "ekadhā": "in one way", "sarvathā": "in every way",
                 "vinā": "without", "ṛte": "without, except", "antareṇa": "without, between", "purā": "formerly", "sākṣāt": "directly", "samam": "together with",
                 "āho": "or", "āhosvit": "or",
                 # spelt as the kosha spells them (kutas for kutaḥ: the particle filter matches the stem), and the common adverbs
                 # a chance nominal would shadow (kathaṃ as the accusative of Edgerton's katha, kutaḥ as a name, tataḥ as tata)
                 "kutas": "whence", "tatas": "then", "katham": "how", "kutra": "where", "yatra": "where", "atra": "here",
                 "anyatra": "elsewhere", "paratra": "elsewhere, in the next world", "sarvatra": "everywhere", "ekatra": "in one place",
                 "sarvadā": "always", "ekadā": "at one time", "anyadā": "at another time", "kadā": "when", "nanu": "surely",
                 "prāk": "before", "jātu": "ever", "kvacit": "anywhere", "kvacana": "anywhere", "kuha": "where",
                 "uta": "and, or", "svayam": "oneself", "antar": "within, inside", "antaḥ": "within, inside"}   # not anyathā, mithyā: members of anyathābhāva, mithyādṛṣṭi
# words run together whose whole the kosha reads as a chance stem (nāpi a noun): the two words they are
SANDHI_PAIRS = {"nāpi": ["na", "api"], "cāpi": ["ca", "api"], "vāpi": ["vā", "api"], "naiva": ["na", "eva"], "caiva": ["ca", "eva"],
                "tathaiva": ["tathā", "eva"], "yathaiva": ["yathā", "eva"], "saiva": ["sā", "eva"], "naitat": ["na", "etat"], "naitad": ["na", "etad"],
                "tadaiva": ["tadā", "eva"], "yadaiva": ["yadā", "eva"], "tathāpi": ["tathā", "api"], "tadāpi": ["tadā", "api"], "yadāpi": ["yadā", "api"],
                "nāsau": ["na", "asau"], "kiṃcāpi": ["kiṃ", "ca", "api"], "yatrāpi": ["yatra", "api"], "tatrāpi": ["tatra", "api"],
                "neti": ["na", "iti"], "ceti": ["ca", "iti"], "yacca": ["yat", "ca"], "tacca": ["tat", "ca"], "athāpi": ["atha", "api"],
                "cāsau": ["ca", "asau"], "nātra": ["na", "atra"], "yāvanna": ["yāvat", "na"], "tāvanna": ["tāvat", "na"],
                "tadeva": ["tad", "eva"], "yadeva": ["yad", "eva"], "etadeva": ["etad", "eva"]}
PARTICLES = set(INDECLINABLES)              # for these the particle is the only reading kept (na is not the pronoun na = ena)
# forms vidyut's kosha lacks or mislays: the perfect āha used as a present, the strong forms of mahat
IRREGULAR_VERBS = {"āha": ("āha", "perf", ["perf 3rd sg", "perf 1st sg"], "says, said (the perfect of √ah, used as a present)"),
                   "āhuḥ": ("āha", "perf", ["perf 3rd pl"], "say, said (the perfect of √ah, used as a present)"),
                   "abhūm": ("bhavati", "aor", ["aor 1st sg"], "I was (the aorist of √bhū; the hybrid form for abhūvam)"),
                   "āhatuḥ": ("āha", "perf", ["perf 3rd dual"], "say, said (the perfect of √ah, used as a present)")}
IRREGULAR_NOMINALS = {
    "ādīni": ("ādi", "adj", ["nt nom pl", "nt acc pl", "nt voc pl"]),   # darśanādīni: the kosha gives only ādin "eating"
    "sat": ("sat", "adj", ["nt nom sg", "nt acc sg"]), "asat": ("asat", "adj", ["nt nom sg", "nt acc sg"]),   # the kosha reads asat as an imperfect of sas
    "ṣaṭ": ("ṣaṣ", "card", ["nt nom pl", "nt acc pl", "masc nom pl", "masc acc pl"]),
    "ādi": ("ādi", "masc", ["masc nom sg", "nt nom sg", "nt acc sg"]),   # darśanādi, śāśvatāśāśvatādi: the kosha has ādi only as an indeclinable
    "trīṇi": ("tri", "card", ["nt nom pl", "nt acc pl"]), "catvāri": ("catur", "card", ["nt nom pl", "nt acc pl"]),   # the numerals' neuter
    "tisraḥ": ("tri", "card", ["fem nom pl", "fem acc pl"]), "catasraḥ": ("catur", "card", ["fem nom pl", "fem acc pl"]),   # and feminine forms
    "pañca": ("pañcan", "card", ["nt nom pl", "nt acc pl", "masc nom pl", "masc acc pl"]), "sapta": ("saptan", "card", ["nt nom pl", "nt acc pl", "masc nom pl", "masc acc pl"]),
    "aṣṭa": ("aṣṭan", "card", ["nt nom pl", "nt acc pl", "masc nom pl", "masc acc pl"]), "aṣṭau": ("aṣṭan", "card", ["masc nom pl", "masc acc pl", "nt nom pl", "nt acc pl"]),
    "nava": ("navan", "card", ["nt nom pl", "nt acc pl", "masc nom pl", "masc acc pl"]), "daśa": ("daśan", "card", ["nt nom pl", "nt acc pl", "masc nom pl", "masc acc pl"]),
    "mahān": ("mahat", "adj", ["masc nom sg"]), "mahāntaḥ": ("mahat", "adj", ["masc nom pl", "masc voc pl"]),
                      "mahāntau": ("mahat", "adj", ["masc nom dual", "masc acc dual"]), "mahāntam": ("mahat", "adj", ["masc acc sg"]),
    "ap": ("ap", "fem", ["fem nom pl", "fem acc pl"]), "āpaḥ": ("ap", "fem", ["fem nom pl", "fem voc pl"])}
# the pronoun forms that end in -e and drop it to -a before a vowel (ta eva = te eva): looked up as the -e form too
E_BEFORE_VOWEL = {"ta": "te", "ya": "ye", "ka": "ke", "ma": "me"}
# the verbal prefixes as they appear in a word (with their sandhi forms), longest first: pary-avāpnoti, sam-anu-paśyati
PREFIX_SURFACES = sorted({"prati", "praty", "pari", "pary", "abhi", "abhy", "adhi", "adhy", "anu", "anv", "upa", "upā", "ava", "api", "apa",
                          "ati", "aty", "sam", "saṃ", "pra", "prā", "vi", "vy", "ni", "ny", "nis", "nir", "niḥ", "niṣ", "niś", "ud", "ut",
                          "un", "uc", "uj", "dur", "dus", "duḥ", "duṣ", "parā", "ā", "śrad", "tiras", "puras"}, key=len, reverse=True)   # tiras-kṛtya
# a finite verb's endings (the plain and the hybrid spellings): a word so ended that the kosha does not know is tried as a prefixed verb
VERB_ENDINGS = ("ti", "te", "nti", "nte", "ṃti", "ṃte", "si", "se", "tha", "mi", "maḥ", "mahe", "dhve", "yāt", "yuḥ", "yām", "yāma", "et", "eyuḥ",
                "eta", "eyam", "tu", "ntu", "ṃtu", "āt", "īt", "iṣuḥ", "sīt", "uḥ", "ire", "ate", "ante", "mahi", "vahi", "mahai", "vahai")
INDEFINITE = ("cit", "cid", "cana", "api")  # kaścit, kecit, kiṃcana: the indefinite pronoun
RARE_TENSES = {"imperf", "perf", "aor", "bened", "cond", "injunctive", "plup", "pfut"}   # the tenses a chance verb reading comes in
VOICED = "gjḍdbnmyrlvhñṅṇ"                  # the consonants before which a visarga is written r (siddhir na) and a final k g (vāg viṣpandaḥ)
PARTICLE_RIGHT = {"iti", "eva", "api", "iva", "ca", "vā", "hi", "tu"}
# the gender of a Buddhist term in its Buddhist use, where Monier-Williams' entry would mislead (sattva "being" is masculine)
GENDER_OVERRIDE = {"sattva": "masc", "bodhi": "fem", "dhātu": "masc", "samādhi": "masc", "śāstṛ": "masc", "kṣetra": "nt", "skandha": "masc",
                   "dharma": "masc", "karman": "nt", "nirvāṇa": "nt", "loka": "masc", "mārga": "masc", "āyatana": "nt", "indriya": "nt",
                   "bhagavat": "masc", "āyuṣmat": "masc", "subhūti": "masc", "sugata": "masc", "tathāgata": "masc", "arhat": "masc", "moha": "masc"}
COMMON_VERBS = {"karoti", "bhavati", "gacchati", "paśyati", "vadati", "bravīti", "vakti", "dadāti", "tiṣṭhati", "āgacchati", "jānāti",
                "śṛṇoti", "manyate", "labhate", "prāpnoti", "viharati", "bhāṣate", "vaktavya", "utpadyate", "nirudhyate", "jāyate", "mriyate",
                "āha", "asti", "syāt", "bhavet", "paśyet", "kurute", "dharati", "carati", "āśrayati", "upasaṃkrāmati", "pratipadyate", "deśayati",
                "ādadāti", "ādatte", "dadāti", "gṛhṇāti", "niṣīdati", "prakrāmati", "pratikrāmati", "āgacchati", "nirgacchati", "praviśati",
                "abhivandate", "praṇamati", "uttiṣṭhati", "pratiṣṭhāpayati", "prakṣālayati", "nivāsayati", "upasthāpayati", "ābhujati",
                "pravartate", "prasavati", "pratilabhate", "udgṛhṇāti", "saṃprakāśayati", "śaknoti",
                "apekṣate", "upapadyate", "prasajyate", "sidhyati", "yujyate", "vidyate", "saṃbhavati", "sambhavati", "ucyate", "dṛśyate",
                "kalpyate", "gamyate", "īkṣate", "labhyate", "prajñāyate", "pratyeti", "varṇayati", "anuvarṇayati", "janayati", "nivartate",
                "pravṛṇoti", "avaiti", "icchati", "abhāṣata", "uvāca", "nirvāti", "nirvāsyati", "parinirvāti",
                "saṃsarati", "pratibādhate", "bādhate", "bhajyate", "īhate", "ajyate", "kalpayati", "vikalpayati", "prajñapayati", "namasyati",
                "vandate", "utpādayati", "nirmimīte", "vartate", "nirundhe"}
SHORT_WORDS = {"na", "ca", "vā", "hi", "tu", "sa", "te", "me", "nu", "ye", "yā", "yo", "ko", "kā", "so", "sā", "ke", "mā", "no", "vo", "tā",
               "tat", "yat", "kim", "sma", "ity", "api", "iti", "iva", "eva", "iha", "yad", "tad", "kva", "u", "ā", "cet", "ced"}
NUMERALS = {"eka", "dvi", "tri", "catur", "pañca", "ṣaṣ", "sapta", "aṣṭa", "aṣṭan", "nava", "daśa", "śata", "sahasra", "koṭi"}
NUMERAL_SANDHI = {"try": "tri", "dvy": "dvi", "ṣaḍ": "ṣaṣ", "ṣaṇ": "ṣaṣ", "ṣaṭ": "ṣaṣ", "a": "na", "an": "na"}
NAME_PREFIXES = {"ārya", "mahā", "śrī", "bhagavat", "su"}
# the persons of the sūtras whose names the dictionaries also know as common words (subhūti "well-being")
NAMES = {"subhūti", "śāriputra", "ānanda", "maitreya", "mañjuśrī", "avalokiteśvara", "dīpaṃkara", "dīpaṅkara", "śākyamuni", "kāśyapa",
         "mahākāśyapa", "maudgalyāyana", "kauṇḍinya", "anāthapiṇḍada", "sudatta", "rāhula", "upāli", "aniruddha", "revata", "pūrṇa",
         "kātyāyana", "samantabhadra", "vajrapāṇi", "akṣobhya", "amitābha", "vairocana", "śrāvastī", "rājagṛha", "vaiśālī", "kapilavastu",
         "magadha", "kośala", "gaṅgā", "sumeru", "jeta", "jetavana", "veṇuvana", "gṛdhrakūṭa", "māra", "indra", "śakra", "brahmā",
         "sahacittotpādadharmacakrapravartin", "sahacittotpādadharmacakrapravartana", "anikṣiptadhura", "mahāsthāmaprāpta",
         "ajitasena", "vakkula", "mahānāman", "nandimitra"}
NOMINAL_POS = ("masc", "fem", "nt", "adj", "pron", "pp", "prp", "ptp", "card")
SUFFIX_PARTS = {"tva", "tā", "ka", "ika", "in", "vat", "mat", "maya", "tara", "tama", "ya", "tas", "vin", "min", "dhā", "śas", "dā", "tra"}
VERB_POS = ("pr", "aor", "fut", "imp", "opt", "cond", "imperf", "perf", "pfut", "bened")
VERBAL_POS = VERB_POS + ("abs", "inf", "pp", "prp", "ptp")   # a finite verb or a form made from one
WORD_CHARS = "a-zāīūṛṝḷḹṃṁḥṅñṭḍṇśṣ’'"
IAST_WORD = re.compile(rf"[{WORD_CHARS}]+", re.I)
VOWELS = "aāiīuūṛṝḷeoAI"
SHORT_MEMBERS = {"tat", "tad", "sat", "sad", "yat", "yad", "sva", "ap", "go", "kha", "bhū", "vāc", "diś", "hṛd"}   # tat-kṣaya, sad-dharma, ab-dhātu: short stems that head compounds
# the root as it stands before -ya in an absolutive, and the present the dictionaries cite the verb by
ABSOLUTIVE_ROOTS = {"kṛt": "karoti", "gam": "gacchati", "bhū": "bhavati", "dā": "dadāti", "sthā": "tiṣṭhati", "jñā": "jānāti", "hṛt": "harati",
                    "dṛś": "paśyati", "labh": "labhate", "āp": "āpnoti", "śru": "śṛṇoti", "gṛh": "gṛhṇāti", "sṛt": "sarati", "vad": "vadati",
                    "pad": "padyate", "sad": "sīdati", "yuj": "yunakti", "dhṛt": "dharati", "vṛt": "vartate", "mṛt": "mriyate", "ī": "eti", "i": "eti"}
NON_MEMBER_PARTICLES = {"ca", "vā", "hi", "tu", "iti", "eva", "api", "iva", "nu", "sma", "u", "atas", "itas", "tatas", "kutas", "yatas"}
PREFIX_ONLY = {"sa", "su", "dus", "dur", "ku"}                # the kosha's nominal entries for sa-, su-, dus-: prefixes, not words
PREFIX_SANDHI = {"niś", "niṣ", "nir", "nis", "niḥ", "duś", "duṣ", "dur", "dus", "duḥ", "saṃ", "sam", "samā", "anv", "abhy", "adhy", "praty",
                 "pary", "upā", "prā", "parā", "udā", "utā"}             # a prefix as Monier-Williams writes it before the member (niś—caya)
PREFIXES = {"a", "an", "su", "dur", "dus", "nis", "nir", "vi", "sam", "saṃ", "pra", "prati", "anu", "upa", "ud", "ut", "ni",
            "pari", "abhi", "adhi", "ati", "apa", "api", "ava", "ā", "parā", "sa"}


def normalise(word: str) -> str:
    """Lower case, ṁ written ṃ, punctuation off; a leading avagraha is the elided ``a``."""
    w = word.replace("ṁ", "ṃ").strip(PUNCT.replace("’", "").replace("‘", "").replace("'", "") + "-–—").lower()
    if w.startswith(("’", "‘", "'")):
        w = "a" + w.lstrip("’‘'")
    return w.strip("’‘'")


def to_slp1(iast: str) -> str:
    return lipi.transliterate(iast.replace("ṁ", "ṃ"), lipi.Scheme.Iast, lipi.Scheme.Slp1)


def to_iast(slp: str) -> str:
    return lipi.transliterate(slp, lipi.Scheme.Slp1, lipi.Scheme.Iast)


def _tag(x) -> str:
    s = str(x)
    return s.split(".")[-1] if s.startswith(("Linga", "Vibhakti", "Vacana", "Purusha", "Lakara", "Prayoga", "Krt")) else s


def key_variants(iast: str) -> list[str]:
    """The pre-sandhi padas, in SLP1, that a word written as it stands in a sentence may be: final visarga for
    ``s``/``r``, anusvāra for ``m``, the sandhi finals ``o``/``ā``/``d``/``c``/``n`` undone, a nasal for anusvāra
    before a stop."""
    out: list[str] = []
    base = to_slp1(iast)
    seen: set[str] = set()

    def add(k: str) -> None:
        if k and k not in seen:
            seen.add(k)
            out.append(k)

    add(base)
    if base.endswith("H"):
        add(base[:-1] + "s"); add(base[:-1] + "r")
    if base.endswith("M"):
        add(base[:-1] + "m")
    if base.endswith(("Ms", "MS", "Ml", "nn", "ns")):
        add(base[:-2] + "n")
    if base.endswith("Y") and len(base) > 2:
        add(base[:-1] + "n")
    if base.endswith("Av"):
        add(base[:-2] + "O")
    if base.endswith("y") and len(base) >= 2:
        add(base[:-1] + "i"); add(base[:-1] + "I")
    if base.endswith("v") and len(base) >= 2:
        add(base[:-1] + "u"); add(base[:-1] + "U")
    if base.endswith("g"):
        add(base[:-1] + "k")
    if base.endswith("b"):
        add(base[:-1] + "p")
    if base.endswith("q"):
        add(base[:-1] + "w")
    if base.endswith("o"):
        add(base[:-1] + "as"); add(base[:-1] + "aH")
    if base.endswith("A"):
        add(base[:-1] + "As"); add(base[:-1] + "AH")
    if base.endswith("kzu") and len(base) > 4:
        add(base[:-3] + "S")                                        # vidikṣu, dikṣu: the locative plural of a stem in -ś
    if base.endswith(("d", "c", "j", "l")):
        add(base[:-1] + "t")
    if base.endswith(("S", "z")) and len(base) > 2:
        add(base[:-1] + "H"); add(base[:-1] + "s"); add(base[:-1] + "t")
    if base.endswith("s") and len(base) > 3:
        add(base[:-1] + "H")                                        # bahavas tāsu: the visarga written s before t
    if base.endswith("r") and not base.endswith("ar"):
        add(base[:-1] + "H"); add(base[:-1] + "s")
    if base.endswith("n") and len(base) > 3:
        add(base[:-1] + "t")
    for k in list(out):
        if "M" in k[:-1]:
            m = re.sub(r"M([kKgG])", r"N\1", k); m = re.sub(r"M([cCjJ])", r"Y\1", m); m = re.sub(r"M([wWqQ])", r"R\1", m)
            m = re.sub(r"M([tTdD])", r"n\1", m); m = re.sub(r"M([pPbB])", r"m\1", m)
            add(m)
        if re.search(r"[NYRnm][kKgGcCjJwWqQtTdDpPbB]", k):
            add(re.sub(r"[NYRnm](?=[kKgGcCjJwWqQtTdDpPbB])", "M", k))
    return out


class SanskritLexicon:
    """The Sanskrit counterpart of :class:`kavi.dpd.DPD`: ``analyse``, ``known``, ``frequency``, ``deconstruct``."""

    language = LANGUAGE
    code = CODE
    pronouns = PRONOUNS

    def __init__(self, data_dir: Path):
        if not HAVE_VIDYUT:                                     # pragma: no cover
            raise RuntimeError("the vidyut package is needed for Sanskrit: uv add vidyut")
        data_dir = Path(data_dir)
        kosha_dir = data_dir / "vidyut" / "kosha"
        if not kosha_dir.exists():
            raise FileNotFoundError(f"vidyut data not found at {kosha_dir} — run `kavi setup --sanskrit`")
        self.kosha = Kosha(str(kosha_dir))
        self.vyakarana = Vyakarana()
        db = data_dir / "sanskrit.sqlite"
        self.cologne: Cologne | None = Cologne(db) if db.exists() else None
        self.version = f"vidyut {data_dir.name}; cologne {'yes' if self.cologne else 'no'}"
        self._stems: set[str] | None = None
        self._analysis: dict[str, Analysis] = {}
        self._lemma_cache: dict[str, str] = {}
        self._direct_cache: dict[str, list[Headword]] = {}
        self._expanding: set[str] = set()                            # the stems whose members are being looked up (no re-entry)
        self._good_cache: dict[str, tuple[int, int] | None] = {}    # _good_info
        self._pos_cache: dict[tuple, str] = {}
        self._sandhi_cache: dict[str, list[list[str]]] = {}
        self._comp_splits_cache: dict[str, list[list[str]]] = {}
        self._hw_id = 0

    # -- helpers ----------------------------------------------------------------------------

    @property
    def stems(self) -> set[str]:
        """Every stem vidyut knows, in IAST (205,000)."""
        if self._stems is None:
            self._stems = {to_iast(p.lemma) for p in self.kosha.pratipadikas()}
        return self._stems

    def stem_known(self, stem: str) -> bool:
        """A stem vidyut knows, or a dictionary headword of at least three letters (the dictionaries list every syllable)."""
        return stem in self.stems or (len(stem) >= 3 and self.cologne is not None and self.cologne.known(stem))

    def real_stem(self, stem: str) -> bool:
        """A stem that is a dictionary headword: the test that tells a word from a form vidyut merely generates."""
        return self.cologne is not None and self.cologne.known(stem)

    def _common_word(self, stem: str) -> bool:
        """The dictionaries list the stem as a word, not only as a proper name."""
        return self.cologne is not None and any(not Cologne.is_name_body(r["body"]) for r in self.cologne.lookup(stem))

    def _edgerton_name(self, stem: str) -> bool:
        """Edgerton lists the stem as a proper name (Śāriputra, Subhūti): a Buddhist name, kept whole."""
        return self.cologne is not None and any(r["source"] == "bhs" and Cologne.is_name_body(r["body"]) for r in self.cologne.lookup(stem))

    def _edgerton_word(self, stem: str) -> bool:
        """Edgerton lists the stem as a word (not only as a name): it is Buddhist Sanskrit usage, not a chance form."""
        return self.cologne is not None and any(r["source"] == "bhs" and not Cologne.is_name_body(r["body"]) for r in self.cologne.lookup(stem))

    def _meaning(self, lemma: str, root_keys: list[str] | None = None) -> tuple[str, str]:
        """(meaning, pali cognate) from the Cologne dictionaries for a stem or a root."""
        if self.cologne is None:
            return "", ""
        cands = [lemma] + ([lemma[:-3] + "in"] if lemma.endswith("ana") and len(lemma) >= 12 else []) + (root_keys or [])
        first_text, first_pali = "", ""
        for key in cands:
            rows = self.cologne.lookup(key)
            if rows:
                text = self.cologne.meaning(key)
                pali = next((r["pali"] for r in rows if r["pali"]), "")
                if not first_text:
                    first_text, first_pali = text, pali
                    if "in this sense not recorded" not in text.lower():
                        return text, pali
                elif text and text != first_text and "in this sense not recorded" not in text.lower():
                    return f"{text}; {first_text}", first_pali or pali
        return first_text, first_pali

    def _verb_lemma(self, dhatu, prayoga_pass: bool = False) -> str:
        """The third person singular present of a root with its prefixes, derived with vidyut-prakriya."""
        key = f"{dhatu}|{prayoga_pass}"
        if key in self._lemma_cache:
            return self._lemma_cache[key]
        lemma = ""
        try:
            pada = Pada.Tinanta(dhatu=dhatu, prayoga=Prayoga.Karmani if prayoga_pass else Prayoga.Kartari, lakara=Lakara.Lat,
                                purusha=Purusha.Prathama, vacana=Vacana.Eka)
            forms = [to_iast(p.text) for p in self.vyakarana.derive(pada)]
            finite = [f for f in forms if f.endswith(("ti", "te"))]
            ranked = sorted(finite, key=lambda f: (f.endswith(("yati", "yate")), f.endswith("te")))
            lemma = (ranked or forms or [""])[0]
        except Exception:
            lemma = ""
        if not lemma:
            lemma = to_iast("".join(dhatu.prefixes or []) + re.sub(r"[\\~^]", "", dhatu.aupadeshika))
        self._lemma_cache[key] = lemma
        return lemma

    def _participle_stem(self, dhatu, krt, surface: str) -> str:
        key = f"{dhatu}|{krt}|stem"
        if key in self._lemma_cache:
            return self._lemma_cache[key]
        stem = ""
        try:
            forms = [to_iast(p.text) for p in self.vyakarana.derive(Pratipadika.krdanta(dhatu, krt))]
            stem = sorted(forms, key=lambda f: f.count("y"))[0] if forms else ""
        except Exception:
            stem = ""
        if not stem:
            stem = re.sub(r"(aḥ|am|ena|āya|āt|asya|e|au|āḥ|ān|aiḥ|ebhyaḥ|ānām|eṣu|ā|a|ṃ|m|ḥ|iḥ|im|īn|īḥ|ī|i|uḥ|um|ū|u)$", "", surface) or surface
        self._lemma_cache[key] = stem
        return stem

    def _root_keys(self, dhatu, clean_text: str = "") -> list[str]:
        """The dictionary headwords a root may stand under: with its prefixes (``nizad`` as vidyut cleans it, ``vi-hṛ``,
        ``utpad``) and bare."""
        aup = re.sub(r"[\\^]", "", dhatu.aupadeshika)
        aup_stripped = re.sub(r"^(?:qu|Yi|wu)", "", aup)
        aup_stripped = re.sub(r"(?:IR|[aAiIuUfFxXeEoO]~[zYR]?|[Ynwq])$", "", aup_stripped)
        bare_clean = to_iast(re.sub(r"[\\~^]", "", aup_stripped))
        bare = to_iast(re.sub(r"[\\~^]", "", dhatu.aupadeshika))
        bare = re.sub(r"[\\~^]", "", bare)
        pre = to_iast("".join(dhatu.prefixes or []))
        keys: list[str] = []
        if clean_text:
            ct = to_iast(clean_text)
            keys.append(ct)
            if pre and ct.startswith(pre):
                keys.append(pre + "-" + ct[len(pre):])
        for b in ([bare_clean, bare] if bare_clean != bare else [bare]):
            if pre:
                keys += [pre + b, pre.replace("ud", "ut") + b, pre.replace("m", "ṃ") + b, pre + "-" + b]
            keys.append(b)
        for k in list(keys):                                  # ṣ for s after i/u in the prefix (ni-ṣad, vi-ṣad)
            if pre and k.startswith(pre) and k[len(pre):].startswith("s"):
                keys.append(k[:len(pre)] + "ṣ" + k[len(pre) + 1:])
        return keys

    def _dictionary_members(self, stem: str) -> list[str]:
        """Monier-Williams writes a compound headword with its members marked, ``boDi—sattva``, ``pra-jYA—pAramitA``
        (``-`` divides a prefix, ``—`` the members): the members in IAST, or nothing."""
        if self.cologne is None:
            return []
        for r in self.cologne.lookup(stem):
            k2 = (r["k2"] or "").split(",")[0].strip().replace("/", "").replace("\\", "").replace("˚", "")
            if not k2 or r["source"] == "ap90" or ("—" not in k2 and "-" not in k2):
                continue
            parts: list[str] = []
            for x in k2.split("—"):
                sub = [to_iast(y) for y in x.split("-") if y]
                if len(sub) >= 2:                                      # a-mala, try-adhva, mahā-sāhasra: the negation, a numeral, two words
                    head = NUMERAL_SANDHI.get(sub[0], sub[0])
                    if head == "na" or head in NUMERALS:
                        parts += [head] + ["".join(sub[1:])]
                        continue
                    if (len(sub) == 2 and sub[0] not in PREFIXES and sub[0] not in PREFIX_SANDHI and len(sub[0]) >= 3 and len(sub[1]) >= 3
                            and self._nominal(sub[0]) and self._nominal(sub[1]) and self._weight(sub[0]) >= 2):   # not upā-dāna
                        parts += sub
                        continue
                    if len(sub) == 2 and sub[0] == "sa" and len(sub[1]) >= 3 and self._nominal(sub[1]):
                        parts += sub                                   # sa-deva: "with the gods", sa a member (the author's sa+deva+mānuṣa+asura)
                        continue
                parts.append("".join(sub))
            parts = [x for x in parts if x]
            if len(parts) >= 2 and parts[-1] in SUFFIX_PARTS:          # śūnya—tā: a suffix, not a member
                return []
            if any((x in PREFIXES and x != "sa") or x in PREFIX_SANDHI for x in parts):   # su—bhūti, niś—caya: a prefix, not a member
                return []
            if len(parts) >= 2 and all(x == "na" or x == "sa" or x in NUMERALS or (len(x) >= 3 and self._nominal(x) and self._weight(x) >= 2) for x in parts):
                return parts                                           # pāra—mitā is Monier-Williams' etymology, not members; svar—ga, taj—ja, prahā—ṇa are not words
        return []

    def _new_id(self) -> int:
        self._hw_id += 1
        return self._hw_id

    # -- headwords from vidyut entries ---------------------------------------------------------------

    def _noun_pos(self, stem: str, lingas: list[str], surface_gender: str = "") -> str:
        """The part of speech of a nominal stem: the dictionaries' gender where they give one (Edgerton's first,
        then Monier-Williams'; ``mfn.`` is an adjective; a compound the dictionaries do not list takes its last
        member's), else vidyut's genders (two or more: an adjective)."""
        ck = (stem, tuple(lingas), surface_gender)
        if ck in self._pos_cache:
            return self._pos_cache[ck]
        dg = self._dict_genders(stem)
        if stem in GENDER_OVERRIDE:
            dg = {GENDER_OVERRIDE[stem]}
        elif is_agent_tr(stem):
            dg = {"masc"}                                            # Pāṇini 3.1.133 ṇvul-tṛcau & 4.1.5 ṛnnebhyo ṅīp: -tṛ agent nouns are masc (fem is -trī)
        elif self._name_only(stem):
            dg = (self.cologne.name_genders(stem) if self.cologne is not None else set()) or dg   # Subhūti the disciple, not subhūti "welfare"
        if dg == {"ind"}:
            pos = "ind"
        else:
            dg.discard("ind")
            real = [l for l in lingas if l]
            counts = self.cologne.gender_counts(stem) if self.cologne is not None else {}
            if "adj" in dg and len(dg) > 1:
                others = {g: n for g, n in counts.items() if g != "adj"}
                if stem in CORE_TERMS or (others and max(others.values()) >= counts.get("adj", 0)):
                    dg.discard("adj")                              # pariṣad, satya, nirvāṇa: the noun is the commoner use
            if "adj" in dg:
                pos = "adj"
            elif len(dg) == 1:
                pos = next(iter(dg))
            elif len(dg) >= 2:
                ranked = sorted(dg, key=lambda g: (-counts.get(g, 0), ("masc", "nt", "fem").index(g) if g in ("masc", "nt", "fem") else 9))
                pos = ranked[0] if counts.get(ranked[0], 0) > counts.get(ranked[1], 0) else (surface_gender if surface_gender in dg else ranked[0])
            elif len(real) >= 2:
                pos = "adj"
            else:
                pos = surface_gender or (real[0] if real else "masc")
        self._pos_cache[ck] = pos
        return pos

    def _dict_genders(self, stem: str) -> set[str]:
        """The dictionaries' genders for a stem, or for the last member of a compound they do not list."""
        if self.cologne is None:
            return set()
        dg = set(self.cologne.genders(stem))
        if not dg:
            members = self._dictionary_members(stem)
            if members:
                dg = set(self.cologne.genders(members[-1]))
        return dg

    def _gender_ok(self, stem: str, lingas: list[str], pos: str, gender: str, loose: bool = False) -> bool:
        """A parse's gender is one the stem has: the dictionaries' where they give one (vidyut's kosha gives every
        stem forms in every gender; rūpa is neuter, śūnyatā feminine, prāpti feminine), else vidyut's; a name's
        gender counts (Subhūti the disciple is masculine); the last member of a compound (``loose``) may be an
        a-stem noun used as an adjective in any gender (śūnyatālakṣaṇā)."""
        if pos in ("adj", "pron", "ind", "card") or not gender:
            return True
        if loose and (stem.endswith("a") or gender == "nt"):
            return True
        if stem in GENDER_OVERRIDE:
            return gender == GENDER_OVERRIDE[stem]
        dg_all = self._dict_genders(stem)
        dg = dg_all & {"masc", "fem", "nt"}
        names = self.cologne.name_genders(stem) if self.cologne is not None else set()
        if names and self._name_only(stem):
            return gender in names                                   # Subhūti: the disciple's gender, not the common noun's
        if dg and "adj" not in dg_all:
            allowed = dg | names
        else:
            allowed = {l for l in lingas if l} | dg | names
        return not allowed or gender in allowed

    def _name_only(self, stem: str) -> bool:
        """A Buddhist proper name: one of the persons of the sūtras (Subhūti, whose stem Monier-Williams also has as
        "well-being"), a stem Edgerton lists only as a name and Monier-Williams not at all as a word (Anāthapiṇḍada),
        or one the dictionaries know only as a name; not pṛthivī or sūrya, the earth and the sun, whom Edgerton has
        only as deities."""
        if stem in NAMES:
            return True
        if self.cologne is None:
            return False
        if self._edgerton_name(stem) and not self._edgerton_word(stem):
            return not any(r["source"] == "mw" and not Cologne.is_name_body(r["body"]) for r in self.cologne.lookup(stem))
        return self.cologne.is_name(stem)

    def _make_noun(self, stem: str, pos: str, parses: list[str], grammar: str, note: str = "") -> Headword:
        """A nominal headword with its dictionary meaning, its kind and the members Monier-Williams marks."""
        meaning, pali = self._meaning(stem)
        kind = _classify(stem, meaning, pali)
        if not kind and len(stem) >= 4 and self._name_only(stem):
            kind = "name"                                            # Subhūti, Anāthapiṇḍada: the dictionaries' name entries
        members = self._dictionary_members(stem) if kind not in ("name", "honorific") else []
        if members and members[0] == "na" and stem in CORE_TERMS:
            members = []                                             # anātman, akuśala: a negated term stays whole
        members = [m[:-1] + "as" if m.endswith("o") and len(m) > 3 and self._nominal(m[:-1] + "as") else m for m in members]   # tato-nidāna: tatas
        if (not members and kind not in ("name", "honorific") and len(stem) >= 9 and stem not in self.stems and stem not in self._expanding
                and not any(r["source"] == "mw" for r in (self.cologne.lookup(stem) if self.cologne is not None else []))):
            self._expanding.add(stem)                               # the split's members are looked up through this method again
            try:
                expanded = self._merge_prefixes(self._expand_members([stem]))   # trisāhasramahāsāhasra: a compound Edgerton alone lists
            finally:
                self._expanding.discard(stem)
            if len(expanded) >= 2 and all(m == "na" or m in NUMERALS or self._weight(m) >= 3 for m in expanded):
                members = expanded                                   # (saṃbahula, anuparindanā: a prefix is not a member)
        construction = " + ".join(members)
        if not members and kind not in ("technical", "honorific", "name"):
            rest = self._negated_rest(stem) if stem[:1] == "a" and len(stem) >= 5 else ""
            if rest and (self._weight(rest) >= 4 or rest in CORE_TERMS):
                construction = f"na + {rest}"                        # asattva: na + sattva, not asat + tva
            elif stem.endswith("tva") and len(stem) > 5 and self.stem_known(stem[:-3]):
                construction = f"{stem[:-3]} + tva"
            elif stem.endswith("tā") and len(stem) > 5 and self.stem_known(stem[:-2]):
                construction = f"{stem[:-2]} + tā"
        return Headword(id=self._new_id(), lemma=LEMMA_SHOWN.get(stem, stem), stem=stem, pos=pos,
                        grammar=grammar + (", comp" if members else "") + (f"; {note}" if note else ""),
                        meaning=meaning, meaning_lit="", meaning_2="", construction=construction, root="", root_meaning="",
                        family_set="", plus_case="", compound_type="samāsa" if members else "",
                        compound_construction=" + ".join(members), parses=list(parses), kind=kind)

    def _add_noun(self, out: dict, stem: str, lingas: list[str], gender: str, case: str, number: str, note: str,
                  is_avyaya: bool = False, generated: bool = False, loose: bool = False) -> None:
        base = stem[:-1] + "a"
        if (stem.endswith("ā") and len(stem) > 4 and self.cologne is not None and not self._common_word(stem)
                and ("adj" in self.cologne.genders(base) or (base not in self.stems and self._negated_rest(base)))):
            stem, lingas = base, ["masc", "fem"]                     # avimalā: the feminine of the adjective avimala
        lemma = LEMMA_SHOWN.get(stem, stem)
        if is_avyaya:
            pos = "ind"
        elif lemma in PRONOUNS or stem in PRONOUNS:
            pos = "pron"
        else:
            pos = self._noun_pos(stem, lingas, gender)
        hk = ("noun", lemma, pos)
        if not self._gender_ok(stem, lingas, pos, gender, loose):
            return
        parse = f"{gender} {case} {number}".strip() if pos != "ind" else ""
        if hk not in out:
            out[hk] = self._make_noun(stem, pos, [parse] if parse else [], pos + (" (kvip)" if generated else ""), note)
        elif parse and parse not in out[hk].parses:
            out[hk].parses.append(parse)

    def _headwords_from_entries(self, key: str, entries, note: str = "", loose: bool = False) -> list[Headword]:
        out: dict[tuple, Headword] = {}
        for e in entries:
            kind_name = type(e).__name__
            if kind_name.endswith("Tinanta"):
                lak = LAKARA.get(_tag(e.lakara), "pr")
                passive = _tag(e.prayoga) in PRAYOGA_PASS
                dhatu = e.dhatu_entry.dhatu
                lemma = self._verb_lemma(dhatu, passive)
                reflx = key.endswith(ATMANEPADA_ENDS)
                parse = ("reflx " if reflx else "") + f"{lak} {PURUSHA.get(_tag(e.purusha), '3rd')} {VACANA.get(_tag(e.vacana), 'sg')}"
                hk = ("verb", lemma, lak, passive)
                if hk not in out:
                    meaning, pali = self._meaning(lemma, self._root_keys(dhatu, getattr(e.dhatu_entry, "clean_text", "") or ""))
                    root = to_iast(getattr(e.dhatu_entry, "clean_text", "") or "")
                    out[hk] = Headword(id=self._new_id(), lemma=lemma, stem=lemma, pos=lak, grammar=lak + (" pass" if passive else "") + (f"; {note}" if note else ""),
                                       meaning=meaning, meaning_lit="", meaning_2=getattr(e.dhatu_entry, "artha_en", "") or "",
                                       construction="", root=f"√{root}" if root else "", root_meaning=getattr(e.dhatu_entry, "artha_sa", "") or "",
                                       family_set="", plus_case="", parses=[parse], kind=_classify(lemma, meaning, pali))
                elif parse not in out[hk].parses:
                    out[hk].parses.append(parse)
                continue
            pe = e.pratipadika_entry
            gender = LINGA.get(_tag(e.linga), "")
            case = VIBHAKTI.get(_tag(e.vibhakti), "")
            number = VACANA.get(_tag(e.vacana), "")
            krt = getattr(pe, "krt", None)
            if krt is not None and type(pe).__name__.endswith("Krdanta"):
                pos, affix = KRT.get(_tag(krt), ("adj", _tag(krt)))
                dhatu = pe.dhatu_entry.dhatu
                verb = self._verb_lemma(dhatu)
                if pos in ("abs", "inf"):
                    hk = (pos, verb)
                    if hk not in out:
                        meaning, pali = self._meaning(verb, self._root_keys(dhatu, getattr(pe.dhatu_entry, "clean_text", "") or ""))
                        out[hk] = Headword(id=self._new_id(), lemma=verb, stem=verb, pos=pos, grammar=f"{pos} of {verb}" + (f"; {note}" if note else ""),
                                           meaning=meaning, meaning_lit="", meaning_2="", construction=f"{verb} + {affix}", root="", root_meaning="",
                                           family_set="", plus_case="", parses=[], kind=_classify(verb, meaning, pali))
                    continue
                stem = self._participle_stem(dhatu, krt, key)
                if pos in ("masc", "fem", "nt") or _tag(krt) not in KRT:   # a primary noun (kṣaya, lakṣaṇa, prāpti): a plain noun
                    self._add_noun(out, stem, [pos] if pos in ("masc", "fem", "nt") else [gender], gender, case, number, note,
                                   generated=_tag(krt) in ("kvip", "kvi~p", "kvi~n"), loose=loose)
                    continue
                hk = ("part", stem, pos)
                parse = f"{gender} {case} {number}".strip()
                if hk not in out:
                    stem_meaning, pali = self._meaning(stem)
                    verb_meaning, _ = self._meaning(verb, self._root_keys(dhatu, getattr(pe.dhatu_entry, "clean_text", "") or ""))
                    verb_meaning = verb_meaning or getattr(pe.dhatu_entry, "artha_en", "") or ""
                    out[hk] = Headword(id=self._new_id(), lemma=stem, stem=stem, pos=pos, grammar=f"{pos} of {verb}" + (f"; {note}" if note else ""),
                                       meaning=verb_meaning or stem_meaning, meaning_lit="", meaning_2=stem_meaning if verb_meaning else "", construction=f"{verb} + {affix}", root="", root_meaning="",
                                       family_set="", plus_case="", parses=[parse], kind=_classify(stem, stem_meaning or verb_meaning, pali))
                elif parse not in out[hk].parses:
                    out[hk].parses.append(parse)
                continue
            stem = to_iast(pe.lemma)
            lingas = [LINGA.get(_tag(l), "") for l in (getattr(pe, "lingas", None) or [])]
            self._add_noun(out, stem, lingas, gender, case, number, note, is_avyaya=bool(getattr(pe, "is_avyaya", False)), loose=loose)
        hws = list(out.values())
        if self.cologne is not None and len(hws) > 1:                 # rūp, nam: a root read as a noun stem, beside real readings
            hws = [h for h in hws if not (h.pos in NOMINAL_POS and h.pos != "pron" and self.cologne.is_root(h.stem))] or hws
        if any(h.pos in ("abs", "inf") for h in hws):                 # utthāya, āśritya: the absolutive, not its avyaya double
            hws = [h for h in hws if not (h.pos == "ind" and h.stem == key and key not in INDECLINABLES)]
        # arhat, sugata, bhagavat: an honorific or a name is a noun, not the participle or the avyaya vidyut derives it from
        def honorific(h: Headword) -> bool:
            return h.kind in ("honorific", "name") or h.stem in HONORIFICS

        nominal_stems = {h.stem for h in hws if h.pos in ("masc", "fem", "nt", "adj")}
        for h in hws:
            if h.pos in ("pp", "prp", "ptp") and honorific(h) and h.stem not in nominal_stems:
                gender = GENDER_OVERRIDE.get(h.stem, "masc")
                h.pos, h.construction, h.grammar = gender, "", gender
                nominal_stems.add(h.stem)
        hws = [h for h in hws if not (h.pos in ("pp", "prp", "ptp", "ind") and honorific(h) and h.stem in nominal_stems)]
        for h in hws:
            self._negation(h)
            h.parses.sort(key=lambda p: _parse_order(p, h.pos))
        prons = {h.stem for h in hws if h.pos == "pron"}                 # kiṃ, tena: the pronoun before the particle
        if prons:
            prons |= {h.stem for h in hws if h.pos == "ind"}
        nominal = {h.stem for h in hws if h.pos in NOMINAL_POS}
        prons |= {h.stem for h in hws if h.pos == "ind" and h.stem.endswith("m") and (h.stem[:-1] in nominal or h.stem[:-1] + "a" in nominal)}   # satyam: the noun before the adverb
        prons |= {h.stem for h in hws if h.pos == "ind" and ((h.stem.endswith("e") and h.stem[:-1] + "a" in nominal)
                                                             or (h.stem.endswith("āt") and h.stem[:-2] + "a" in nominal))}   # kāle, antikāt: the noun's case form
        stems = {(h.stem, h.pos) for h in hws}
        # amalā beside amala: the ā-stem is the adjective's feminine unless Edgerton lists it as a word
        shadowed = {h.stem for h in hws if h.stem.endswith("ā") and h.pos in ("fem", "adj") and self.cologne is not None
                    and any((h.stem[:-1] + "a", p) in stems for p in ("adj", "pp", "ptp", "prp")) and not self._edgerton_word(h.stem)}
        # mahān: the stems the form reaches as written, before those it reaches through a sandhi variant (maha, read with -t)
        exact_stems = {to_iast(e.pratipadika_entry.lemma) for e in self.kosha.get(to_slp1(key)) if hasattr(e, "pratipadika_entry")}
        hws.sort(key=lambda h: self._rank(h, key, h.stem in prons, h.stem in shadowed, not exact_stems or h.stem in exact_stems))
        seen_abs: set[tuple] = set()                                 # ādāya: ādadāti and āyacchati are one root entry; keep the better ranked
        kept = []
        for h in hws:
            sig = (h.pos, h.meaning) if h.pos in ("abs", "inf") and h.meaning else None
            if sig is not None:
                if sig in seen_abs:
                    continue
                seen_abs.add(sig)
            kept.append(h)
        return kept

    def _rank(self, h: Headword, key: str, pron_too: bool = False, shadowed: bool = False, exact_form: bool = True) -> tuple:
        """Function words spelt like the form first, then pronouns, third-person verbs, real dictionary words (the
        commoner first: the dictionaries have more to say about it), then the forms vidyut generates from obscure
        roots (kvip agent nouns of ``may``, ``mī``) and the masculine forms it gives a feminine ā-stem. A glossary
        term is the noun before the participle (nirvāṇa); a participle comes before the adjective entry that
        duplicates it (śruta); a feminine ā-stem that is only an adjective's feminine (amalā) after the adjective."""
        real = self.real_stem(h.stem) or h.stem in COMMON
        exact = h.stem == key or h.stem == key.rstrip("ṃ") + "m" or h.lemma == key
        weight = self.cologne.weight(h.stem) if self.cologne is not None else 0
        dg = self.cologne.genders(h.stem) if self.cologne is not None else set()
        if h.stem.endswith("ā") and h.parses and all(p.startswith("masc") for p in h.parses) and h.pos != "pron":
            return (6, 0, 0, 0, 0)
        if h.pos == "ind" and exact:
            return (3 if pron_too and h.stem not in INDECLINABLES else (1 if pron_too else 0), 0, 0, 1, 3)
        if h.pos == "ind" and h.stem in INDECLINABLES:
            return (4, 0, 0, 1, 3)                                   # yāvantaḥ: the adjective yāvat, the particle only when spelt so
        if h.pos == "pron":
            return (1, 0 if real else 1, 0, 0, 0)
        if (h.stem in NUMERALS or h.stem.rstrip("n") in NUMERALS or h.pos == "card") and h.pos not in ("pp", "prp", "ptp"):
            return (1, 1, 0 if h.pos == "card" or h.stem.endswith("n") else 1, 0, 0)   # catvāraḥ: catur, not catvāra; aṣṭau: aṣṭan, not the participle aṣṭa
        generated = "(kvip)" in (h.grammar or "") or (h.construction or "").endswith(("kvi~p", "+ ", "+ a")) or (h.pos == "adj" and not real and len(h.stem) <= 3)
        if h.pos in NOMINAL_POS and h.pos != "pron" and self.cologne is not None and self.cologne.is_root(h.stem):
            return (5, 2, 0, 1, 1)                                   # nam, vid: a root read as a noun stem
        if h.pos in VERB_POS:
            third = any("3rd" in p for p in h.parses)
            return (3 if h.pos == "pfut" else (2 if third else 3), 0 if real or h.meaning else 1, 0, 0, 0 if h.lemma in COMMON_VERBS else 1)
        if h.pos in ("pp", "prp", "ptp") and h.compound_type == "negation" and self._common_verb(self._verb_of(h)):
            return (2, 0, 0, 0, 0)                                   # asati: na + sat of asti before a chance present of as "throw"
        if h.pos in ("pp", "prp", "ptp", "abs", "inf"):
            noun_like = h.stem in CORE_TERMS or (bool(dg & {"masc", "fem", "nt"}) and "adj" not in dg)
            real = real or h.pos in ("abs", "inf")                     # an absolutive the kosha or the verb table gives is a reading
            if h.pos in ("abs", "inf"):
                weight = 0                                                # the verb's lemma may collide with a noun (vasati f.)
                if self.cologne is not None and "ind" in self.cologne.genders(key):
                    weight = 24                                           # utthāya, ādāya: Monier-Williams lists the absolutive itself
                elif h.pos == "abs" and key.endswith("ya") and any(h.lemma.startswith(p) for p in PREFIXES if len(p) >= 2):
                    weight = 24                                           # abhivandya: a prefixed verb's absolutive in -ya, the usual reading
            band = 0 if weight < 4 else (1 if weight < 10 else 2)
            return (3 if real else 4, (1 if generated else 0) + (2 if noun_like else 0), -band, 0,
                    (1 if h.pos == "prp" else 0) + (0 if h.pos not in ("abs", "inf") or h.lemma in COMMON_VERBS else 1))
        shadow = (h.pos == "fem" and h.stem.endswith("ā") and len(h.stem) > 3 and self.cologne is not None
                  and "adj" in self.cologne.genders(h.stem[:-1] + "a") and not self._edgerton_word(h.stem))
        band = 0 if weight < 4 else (1 if weight < 10 else 2)      # rare, ordinary, common: lakṣaṇa (22) before lakṣaṇā (6)
        name_penalty = 1 if h.kind == "name" and not self._name_only(h.stem) else 0   # Subhūti, a Buddhist name, before a rare adjective
        voc_only = (1 if h.kind not in ("name", "honorific") and h.parses and weight < 10 and all("voc" in p or "dual" in p for p in h.parses)
                    else 0)                                          # vande: the verb before a chance vocative or dual (vandā); not ārya, Subhūte
        return (3 if real else 5, (1 if generated else 0) + name_penalty + (1 if shadow or shadowed else 0) + (0 if exact_form else 1) + voc_only,
                -band, 0 if exact else 1, 2 if h.pos == "adj" else 1)

    def _negated_rest(self, stem: str) -> str:
        """``anutpanna`` -> ``utpanna`` when the dictionaries analyse the word as a negation (Monier-Williams writes
        its headword ``an-utpanna``); for a word they do not list, when the rest is a known stem."""
        if self.cologne is not None:
            mw = [r for r in self.cologne.lookup(stem) if r["source"] == "mw"]
            for r in mw:
                k2 = (r["k2"] or "").replace("/", "").replace("\\", "")
                m = re.match(r"^(a|an)-(.+)$", k2)
                if m:
                    return to_iast(m.group(2).replace("-", "").replace("—", ""))
            if mw:
                return ""
        if stem.startswith("an") and stem[2:3] in "aāiīuūṛeo" and len(stem) > 4 and self.stem_known(stem[2:]):
            return stem[2:]
        if stem.startswith("a") and len(stem) > 3 and stem[1:2] not in "aāiīuūṛeoṃḥ" and self.stem_known(stem[1:]):
            return stem[1:]
        return ""

    def _negation(self, h: Headword) -> None:
        """``anutpanna`` -> na + utpanna + ta: the author's convention shows a negated word as a compound."""
        s = h.stem
        if h.kind in ("name", "honorific") or len(s) < 4 or s in CORE_TERMS:
            return
        parts = [p.strip() for p in h.construction.split(" + ")] if h.construction else []
        if h.pos in ("pp", "prp", "ptp"):
            if len(parts) != 2 or parts[0] == "na":
                return
            rest = self._negated_rest(s)
            if rest:
                h.construction = f"na + {rest} + {parts[1]}"
                h.grammar = h.grammar.split(";")[0] + ", comp"
                h.compound_type = "negation"
                h.compound_construction = f"na + {rest}"
            return
        if h.pos not in ("adj", "masc", "fem", "nt"):
            return
        if parts and not (len(parts) == 2 and parts[0] == "na"):
            return                                                   # a compound of other members: leave it
        rest = parts[1] if parts else self._negated_rest(s)
        if not rest:
            return
        base = self._direct(rest + ("ḥ" if rest.endswith("a") else "")) or self._direct(rest)
        part = next((b for b in base if b.pos in ("pp", "prp", "ptp") and b.stem == rest), None)
        if part is not None:
            h.pos = part.pos
            h.grammar = part.grammar.split(";")[0] + ", comp"
            h.construction = f"na + {rest} + {part.construction.split(' + ')[-1]}"
            if not h.meaning:
                h.meaning = "not " + (part.meaning or "")
        else:
            h.grammar = (h.grammar.split(",")[0] if h.grammar else h.pos) + ", comp"
            h.construction = " + ".join(["na"] + self._expand_members([rest]))
        h.compound_type = "negation"
        h.compound_construction = h.construction if part is None else f"na + {rest}"

    def _direct(self, key: str, note: str = "", loose: bool = False) -> list[Headword]:
        ck = f"{key}\x01{note}\x01{int(loose)}"
        if ck in self._direct_cache:
            return self._direct_cache[ck]
        if key in IRREGULAR_VERBS:                                    # āha: the perfect used as a present, as the author writes it
            lemma, lak, parses, meaning = IRREGULAR_VERBS[key]
            out = [Headword(id=self._new_id(), lemma=lemma, stem=lemma, pos=lak, grammar=lak + (f"; {note}" if note else ""), meaning=meaning,
                            meaning_lit="", meaning_2="", construction="", root="√ah", root_meaning="", family_set="", plus_case="",
                            parses=list(parses), kind="")]
            self._direct_cache[ck] = out
            return out
        entries = []
        for k in key_variants(key):
            entries.extend(self.kosha.get(k))
        exact_entries = list(entries)
        visarga_lost = False
        if key.endswith("a") and len(key) >= 2:
            # sa, caitya bhūto, anāgāmina evaṃ, dharma utpadyate: -aḥ loses its visarga before a vowel; read so for a short
            # word, a word the kosha does not know as written, or one whose own stem it knows only as a vocative (not anena,
            # asya, nāma; dharma is a vocative of dharma whatever dharman's neuter forms say)
            exact = self.kosha.get(to_slp1(key))
            same = [e for e in exact if not type(e).__name__.endswith("Tinanta") and getattr(e, "pratipadika_entry", None) is not None
                    and to_iast(e.pratipadika_entry.lemma) == key]
            only_voc = all(VIBHAKTI.get(_tag(e.vibhakti), "") == "voc" for e in same)
            visarga_lost = len(key) <= 3 or only_voc
            if visarga_lost:
                for k in (to_slp1(key)[:-1] + "as", to_slp1(key)[:-1] + "aH"):
                    entries.extend(self.kosha.get(k))
        if key in E_BEFORE_VOWEL:                                     # ta eva: te with its e read a before the vowel
            entries.extend(self.kosha.get(to_slp1(E_BEFORE_VOWEL[key])))
        out = self._headwords_from_entries(key, entries, note, loose) if entries else []
        if visarga_lost and len(key) > 3:                              # dharma utpadyate: the readings only the -aḥ lookup gives
            exact_out = self._headwords_from_entries(key, exact_entries, note, loose) if exact_entries else []
            own = {(h.stem, h.pos) for h in exact_out if h.parses and not all("voc" in x for x in h.parses)}
            for h in out:
                if h.parses and not all("voc" in x for x in h.parses) and (h.stem, h.pos) not in own:
                    h.grammar += "; nom with the visarga lost before a vowel"   # also asatī nom pl for asatya, not dharman for dharma
        if key in IRREGULAR_NOMINALS and not any(h.stem == IRREGULAR_NOMINALS[key][0] for h in out):
            stem, pos, parses = IRREGULAR_NOMINALS[key]           # mahān: the strong forms of mahat the kosha lacks; asat before the kosha's imperfect of sas
            out.insert(0, self._make_noun(stem, pos, parses, pos, note))
        if key.endswith("r") and not key.endswith("ar"):               # dhātur: dhātuḥ before the genitive of dhātṛ
            out.sort(key=lambda h: 1 if h.stem.endswith("ṛ") and h.parses and all(p.split()[1] in ("gen", "abl") for p in h.parses if len(p.split()) > 1) else 0)
        for h in out:
            if h.stem in ("dvi", "ubha"):                              # dve: the numeral two has no singular, and the kosha lacks its
                duals = DUAL_FORMS.get(key) or [p for p in h.parses if "dual" in p]   # feminine and neuter dual
                if duals:
                    h.parses = duals
        if key.endswith("n"):                                          # svabhāvaśūnyān: the accusative plural before the ablative read with t
            for h in out:
                h.parses.sort(key=lambda p: 1 if "abl sg" in p else 0)
        ind = next((to_iast(k) for k in key_variants(key) if to_iast(k) in INDECLINABLES), None)
        if ind is None and visarga_lost:                              # kuta eva: kutaḥ with its visarga lost before the vowel
            ind = next((c for c in (key[:-1] + "as", key[:-1] + "aḥ") if c in INDECLINABLES), None)
        if ind and not any(h.pos == "ind" for h in out):
            meaning, _ = self._meaning(ind)
            members = self._dictionary_members(ind)                   # tadyathā: tad + yathā
            out.insert(0, Headword(id=self._new_id(), lemma=ind, stem=ind, pos="ind", grammar="ind" + (", comp" if members else "") + (f"; {note}" if note else ""),
                                   meaning=meaning or INDECLINABLES[ind], meaning_lit="", meaning_2="", construction=" + ".join(members), root="",
                                   root_meaning="", family_set="", plus_case="", compound_type="samāsa" if members else "",
                                   compound_construction=" + ".join(members), parses=[], kind=""))
        if ind in PARTICLES:
            out = [h for h in out if h.pos == "ind" and (h.stem == ind or h.stem in INDECLINABLES)]   # vā: not the particle u the kosha spells vā
        out = [h for h in out if not (h.pos in ("masc", "fem", "nt", "adj") and h.stem != key and h.stem.endswith(("ti", "te")) and len(h.stem) > 4
                                      and any(v.pos in VERB_POS for v in self._direct(h.stem)))] or out   # janayate: no feminine janayati
        if key in COMMON_VERBS:                                        # asti: the verb, not Edgerton's asseverative particle
            out = [h for h in out if not (h.pos == "ind" and h.stem == key)] or out
        out = [h for h in out if not (h.pos in NOMINAL_POS and h.pos != "pron" and h.stem in PREFIX_ONLY)] or out   # sa: the pronoun, not the prefix sa-
        if not out or all(h.kind == "name" or h.stem in ("kiṃcid", "kaścid") for h in out):
            out = self._indefinite(key, note) or out
        if not out and key.endswith(("taḥ", "tas")) and len(key) >= 6:   # vikalpataḥ, dhātutaḥ: the adverb in -tas (tasil) on a known stem
            base = key[:-3]
            if self._nominal(base) and self._weight(base) >= 3 and (self.cologne is None or not self.cologne.is_root(base)):
                out = [Headword(id=self._new_id(), lemma=base + "tas", stem=base + "tas", pos="ind", grammar="ind; adverb in -tas" + (f"; {note}" if note else ""),
                                meaning=f"from {base}, in terms of {base}", meaning_lit="", meaning_2="", construction=f"{base} + tas", root="",
                                root_meaning="", family_set="", plus_case="", parses=[], kind="")]
        if key.endswith("i") and len(key) > 3 and self.cologne is not None and self._nominal(key):
            genders = self.cologne.genders(key) & {"masc", "fem"}
            if genders and not any(h.stem == key and any("voc sg" in p for p in h.parses) for h in out):
                g = "fem" if "fem" in genders else "masc"        # bodhi svāhā: the vocative in -i (Edg. § 10.33)
                voc = next((h for h in out if h.stem == key and h.pos not in VERB_POS), None)   # not a parse of the verb janayati
                if voc is not None:
                    voc.parses.append(f"{g} voc sg")
                else:                                               # after the verbs, pronouns and participles (sati: sat; not bodhin for bodhi)
                    after = sum(1 for h in out if h.pos in VERB_POS or h.pos in ("pron", "pp", "prp", "ptp"))   # (santi is asti, sati is sat)
                    out.insert(after, self._make_noun(key, g, [f"{g} voc sg"], g, (note + "; " if note else "") + "BHS § 10.33 vocative in -i"))
        self._direct_cache[ck] = out
        return out

    def _indefinite(self, key: str, note: str = "") -> list[Headword]:
        """kaścit, kecit, kiṃcana, kadācit: the pronoun or adverb with the indefinite particle."""
        for suf in INDEFINITE:
            if not key.endswith(suf) or len(key) <= len(suf) + 1:
                continue
            base = key[:-len(suf)]
            hws = [h for h in self._direct(base) if (h.pos == "pron" and h.stem == "kim") or (h.pos == "ind" and base.startswith("k"))]
            if not hws:
                continue                                             # anyasmād api: two words
            h = hws[0]
            particle = "cit" if suf == "cid" else suf
            lemma = (base if h.pos == "ind" else "kaś") + particle if h.pos == "ind" or h.stem == "kim" else key
            return [replace(h, id=self._new_id(), lemma=lemma, stem=lemma, grammar=h.pos + ", indefinite" + (f"; {note}" if note else ""),
                            meaning="someone, something, any; (with na) no one, nothing", construction=f"{h.lemma} + {particle}",
                            compound_type="", compound_construction="", parses=list(h.parses), kind="")]
        return []

    def _resolve(self, word: str, loose: bool = False) -> tuple[list[Headword], str]:
        """Headwords for a form as it stands: the kosha, a regular inflection of a dictionary stem, or a hybrid
        spelling's classical reading (with the note that says so)."""
        hws = self._direct(word, loose=loose)
        if not hws:
            hws = self._absolutive(word)                             # praṇāmya: the absolutive before a chance noun reading
        if (not any(h.pos in VERB_POS or h.pos in ("abs", "inf") for h in hws)
                and re.sub(r"[śṣr]$", "ḥ", re.sub(r"d$", "t", word)).endswith(VERB_ENDINGS)):   # anuprāpnuyuś, paryavāpnuyād: the sandhi finals
            verbs = self._prefixed_verb(word)                        # samanupaśyati, paryavāpnuyāt: a prefixed verb the kosha lacks
            if verbs:
                hws = sorted(hws + verbs, key=lambda h: self._rank(h, word))
        if not hws and len(word) >= 7:
            hws = self._prefixed_verb(word)                          # anuvarṇitām: anu + varṇita, the participle of a prefixed verb
        if not any(h.pos in VERB_POS for h in hws) and re.sub(r"[śṣr]$", "ḥ", re.sub(r"d$", "t", word)).endswith(VERB_ENDINGS):
            for cand, why in readings(word)[:6]:                     # janayate: the middle ending on an active verb (Edg. § 37.24)
                m = re.match(r"§ (\d+)", why)
                if not m or int(m.group(1)) < 25 or (hws and not why.startswith("§ 37.")):
                    continue                                         # a verb rule; beside other readings only the voice rules (not sati as santi)
                verbs = [h for h in self._direct(cand, note=f"BHS {why}") if h.pos in VERB_POS and (not hws or self._common_verb(h.lemma))]
                if verbs:                                            # beside other readings only for a common verb (not mahate as mahati)
                    hws = sorted(hws + verbs, key=lambda h: self._rank(h, word))
                    break
        elif hws and len(word) >= 7 and all(self._chance_verb(h) for h in hws):
            participles = [h for h in self._prefixed_verb(word) if h.pos in ("pp", "prp", "ptp", "abs")]
            if participles:
                hws = participles + hws                              # upādattam: upā + datta before the chance imperfect upadadāti
        weak = not hws or not any((h.pos in NOMINAL_POS and self.cologne is not None and self.cologne.weight(h.stem) >= 4)
                                  or (h.pos == "ind" and h.stem in INDECLINABLES) or h.pos in ("pron", "abs", "inf")
                                  or (h.pos in VERB_POS and (h.meaning or h.lemma in COMMON_VERBS)) for h in hws)
        if hws and word.endswith(("ya", "tvā")) and not any(h.pos in ("abs", "inf") for h in hws):
            abs_hws = self._absolutive(word)                         # abhivandya, pratiṣṭhāpya: the absolutive beside the adjective
            if abs_hws:
                hws = [h for h in hws if not (h.pos == "ind" and h.stem == word and word not in INDECLINABLES)]   # parityajya: not its avyaya double
                hws = sorted(hws + abs_hws, key=lambda h: self._rank(h, word))
        if weak:                                                    # vastuṃ: the noun vastu (a hybrid accusative) beside the infinitive
            seen = {h.stem for h in hws}
            extra = [h for h in self._by_model(word, loose) if h.stem not in seen]
            if hws and not extra:
                for cand, why in readings(word)[:4]:
                    extra = [h for h in (self._direct(cand, note=f"BHS {why}", loose=loose) or self._by_model(cand, loose)) if h.stem not in seen]
                    if extra:
                        break
            if hws and not extra and not any(h.pos in ("abs", "inf") for h in hws):
                extra = self._absolutive(word)                       # praṇāmya beside a chance noun form
            if extra:
                hws = sorted(hws + extra, key=lambda h: (self._oblique_agent(h), self._rank(h, word)))
        if hws:
            if word[:1] == "a" and not any(h.pos == "abs" for h in hws):
                neg = self._negation_headword(word, [])              # anupādāya: na + upādāya before the dative of a stem vidyut invents
                if neg is not None and (neg.pos == "abs" or self._junk_reading(hws) or all(self._obscure_verbal(h) for h in hws)):
                    hws = [neg] + hws                                # apaśyamānaṃ: na + paśyamāna, not a participle of apaśyati
            return hws, ""
        # an initial consonant changed by the sandhi with the word before: tasmāc chāriputra, bhāṣyamāṇāṃ cchrutvā, kasmād dhetoḥ
        for written, read, why, min_len in (("cch", "ś", "initial ś written cch after ṃ", 0), ("ch", "ś", "initial ś written ch after t", 0),
                                            ("dh", "h", "initial h written dh after d", 4)):
            if word.startswith(written) and len(word) >= min_len:
                alt = read + word[len(written):]
                hws = self._direct(alt, loose=loose) or self._by_model(alt, loose)
                if hws:
                    return hws, f"read as {alt} ({why})"
        if word.endswith("tvā") and len(word) >= 5 and word[-4] in "aāiīuūṛeo":
            alt = word[:-3] + "ttvā"                                 # datvā: dattvā with the cluster simplified (BHS)
            hws = self._direct(alt, note="tt written t before vā (BHS)", loose=loose) or self._absolutive(alt)
            if hws:
                return hws, ""
        if word.endswith(("ta", "sa", "dhva", "maha")) and len(word) >= 5:   # utpadyata ime: a verb's final e written a before a vowel
            alt = word[:-1] + "e"
            hws = [h for h in (self._direct(alt, note="final e written a before a vowel", loose=loose) or self._prefixed_verb(alt))
                   if h.pos in VERB_POS]
            if hws:
                return hws, ""
        for cand, why in readings(word):
            hws = self._direct(cand, note=f"BHS {why}", loose=loose) or self._by_model(cand, loose)
            if hws:
                return hws, f"read as {cand} (Edg. {why})"
        return self._absolutive(word), ""

    def _absolutive(self, word: str) -> list[Headword]:
        """``vivarjayitvā``: the absolutive of a verb the kosha knows in its finite form (vivarjayati)."""
        for suffix, affix in (("itvā", "tvā"), ("tvā", "tvā"), ("ya", "ya")):
            if not word.endswith(suffix) or len(word) <= len(suffix) + 2:
                continue
            base = word[:-len(suffix)]
            bases = [base]
            short = re.sub(r"ā([^aāiīuūeo]+)$", r"a\1", base)           # praṇām-ya: the root's vowel lengthened for the causative
            if short != base:
                bases.append(short)
            for b, ending in ((b, e) for b in bases for e in ("ati", "ate", "ayati", "ayate", "ti", "te")):
                verbs = [h for h in self._direct(b + ending) if h.pos in VERB_POS]
                if not verbs and b in ABSOLUTIVE_ROOTS and ending == "ati":
                    verbs = [h for h in self._direct(ABSOLUTIVE_ROOTS[b]) if h.pos in VERB_POS]   # tiras-kṛtya: karoti
                prefix = ""
                if not verbs:                                        # abhivandya: the kosha knows vandate, not abhivandate
                    for p in sorted((p for p in PREFIXES if len(p) >= 2 and b.startswith(p) and len(b) > len(p) + 2), key=len, reverse=True):
                        verbs = [h for h in self._direct(b[len(p):] + ending) if h.pos in VERB_POS]
                        if verbs:
                            prefix = p
                            break
                if verbs:
                    v = verbs[0]
                    lemma = prefix + v.lemma
                    return [Headword(id=self._new_id(), lemma=lemma, stem=lemma, pos="abs", grammar=f"abs of {lemma}", meaning=v.meaning,
                                     meaning_lit="", meaning_2="", construction=f"{lemma} + {affix}", root=v.root, root_meaning=v.root_meaning,
                                     family_set="", plus_case="", parses=[], kind=v.kind)]
        return []

    def _prefixed_verb(self, word: str, depth: int = 0) -> list[Headword]:
        """``samanupaśyati``, ``paryavāpnuyāt``, ``udgrahīṣyanti``: a finite verb (or participle) the kosha knows only
        without its prefixes, read by taking the prefixes off as they stand in the word (one or two of them) and
        putting them back on the verb's lemma: sam + anu + paśyati, pary + av + āpnoti."""
        out: list[Headword] = []
        for p in PREFIX_SURFACES:
            if not word.startswith(p) or len(word) - len(p) < 4:
                continue
            rest = word[len(p):]
            if rest[:1] in "aāiīuūṛeo" and p[-1:] in "aāiīuū" and p != "ā":
                continue                                             # upa + a… would have joined: the surface shows the sandhi form
            found = [h for h in self._direct(rest) if h.pos in VERBAL_POS]
            if not found:                                            # Pāṇini 8.4.14 ṇatva & 8.3.59 ṣatva across prefix boundary (praṇamati, pratiṣṭhita)
                for r_alt in undo_natva(p, rest) + undo_satva(p, rest):
                    found = [h for h in self._direct(r_alt) if h.pos in VERBAL_POS]
                    if found:
                        break
            if rest.endswith("ya") and not any(h.pos == "abs" for h in found):
                found = self._absolutive(rest) + found                 # tiras-kṛtya: the absolutive of karoti the kosha gives only prefixed
            why = ""
            if not found:
                for cand, note in readings(rest)[:4]:                # gṛhīṣyaṃti: the hybrid spelling of the rest
                    found = [h for h in self._direct(cand, note=f"BHS {note}") if h.pos in VERBAL_POS]
                    if found:
                        why = note
                        break
            if not found and depth < 1:
                found = self._prefixed_verb(rest, depth + 1)
            if not found:
                continue
            found.sort(key=lambda h: 0 if h.pos == "abs" else 1)       # tiras-kṛtya: the absolutive of karoti before the gerundive of kṛt
            seen_lemmas = set()
            for v in found[:3]:
                base = v.lemma if v.pos in VERB_POS or v.pos in ("abs", "inf") else v.stem
                lemma = p + base
                if lemma in seen_lemmas:
                    continue
                seen_lemmas.add(lemma)
                grammar = re.sub(r"\bof (\S+)", lambda m: f"of {p}{m.group(1)}", v.grammar.split(";")[0], count=1)   # prp of tyajati -> prp of parityajati
                out.append(Headword(id=self._new_id(), lemma=lemma, stem=lemma, pos=v.pos, grammar=grammar + f"; prefixed {p}-" + (f"; BHS {why}" if why else ""),
                                    meaning=self._meaning(lemma)[0] or v.meaning, meaning_lit="", meaning_2=v.meaning_2,
                                    construction=(p + v.construction) if v.construction else "", root=v.root, root_meaning=v.root_meaning,
                                    family_set="", plus_case="", parses=list(v.parses), kind=""))
            if out:
                break
        return out

    # -- the regular inflection of a dictionary stem ---------------------------------------------------

    def _by_model(self, key: str, loose: bool = False) -> list[Headword]:
        """``tathāgatasya``: the ending read on a model stem, the stem looked up in the dictionaries."""
        out: list[Headword] = []
        for (final, gender), model in MODELS.items():
            for ending_len in range(1, 8):
                if ending_len >= len(key):
                    break
                stem_part, ending = key[:-ending_len], key[-ending_len:]
                stem = stem_part + final
                if final in ("a", "ā", "i", "u", "ī", "ū", "ṛ"):
                    model_form = model[:-1] + ending if model.endswith(final) else None
                else:
                    model_form = model[: -len(final)] + ending if model.endswith(final) else None
                if model_form is None or not stem or len(stem) < 3:
                    continue
                if final in ("ā", "ī", "ū") and ending in ("a", "i", "u"):
                    continue                                         # ahetukata is no form of ahetukatā
                if stem.endswith(("ti", "te")) and len(stem) > 4 and any(h.pos in VERB_POS for h in self._direct(stem)):
                    continue                                         # janayate: not a feminine janayati; the verb with a middle ending
                adj_fem = final == "ā" and not self._nominal(stem) and "adj" in self._dict_genders(stem[:-1] + "a")
                abstract = base = ""
                if not self._nominal(stem) and not adj_fem and final in ("a", "ā"):
                    for suf, apos in (("tva", "nt"), ("tā", "fem")):   # anyatva, nirapekṣatva, ahetukatā: the abstract of a known stem
                        if stem.endswith(suf) and len(stem) > len(suf) + 2:
                            cut = stem[:-len(suf)]
                            if self._nominal(cut) and (self._weight(cut) >= 4 or (len(cut) >= 6 and self.cologne is not None and self.cologne.known(cut))):
                                abstract, base = suf, cut            # nirapekṣatva; not āhetukatā on a stem only vidyut lists
                            elif cut[:1] == "a":                   # anantavattva: na + antavat + tva
                                rest = next((r for r in self._negation_rests(cut) if len(r) >= 4 and self._nominal(r) and self._weight(r) >= 4), "")
                                if rest:
                                    abstract, base = suf, "na + " + rest
                            if abstract and apos != gender:
                                abstract = ""                        # the abstract's own gender only
                            if abstract:
                                break
                negated = ""                                         # anirodha, anirgama: na + a stem the dictionaries know
                if not self._nominal(stem) and not adj_fem and not abstract and stem[:1] == "a" and len(stem) >= 6:
                    negated = next((r for r in self._negation_rests(stem) if len(r) >= 4 and self._nominal(r)
                                    and ((self.cologne.weight(r) if self.cologne is not None else self._weight(r)) >= 4 or r in CORE_TERMS)
                                    and not any(b.compound_type == "negation" or (b.construction or "").startswith("na + ")
                                                for b in self._direct(r + ("ḥ" if r.endswith("a") else "")) or self._direct(r))), "")   # not amiti, not an + asādhya
                taddhita = ""
                if not self._nominal(stem) and not adj_fem and final in ("a", "ā", "ī"):
                    s_a = stem[:-1] + "a" if final in ("a", "ā") else stem[:-1]   # pratyayavatī: the feminine of pratyayavat
                    for suf in ("ika", "aka", "ka", "tara", "tama", "maya", "vat", "mat", "vin", "min", "ya"):   # paścimika, pratyayavat: a suffix on a known stem
                        cut = s_a[: -len(suf)] if s_a.endswith(suf) else ""
                        if cut and len(cut) >= 3:
                            if self._nominal(cut) or self._nominal(cut + "a"):
                                taddhita, base = suf, (cut if self._nominal(cut) else cut + "a")
                                break
                            if suf in ("ika", "ya"):                 # Pāṇini 7.2.117 taddhiteṣv acām ādeḥ: undo initial vṛddhi (laukika -> loka, daurmanasya -> durmanas)
                                v_base = next((vb for cand in (cut, cut + "a") for vb in undo_initial_vrddhi(cand) if self._nominal(vb) and self._weight(vb) >= 4), "")
                                if v_base:
                                    taddhita, base = suf, v_base
                                    break
                if not self._nominal(stem) and not adj_fem and not taddhita and not negated and not abstract:
                    continue
                entries = [e for k in key_variants(model_form) for e in self.kosha.get(k)]
                entries = [e for e in entries if type(e).__name__.endswith("Subanta")
                           and (model == "kartṛ" or not type(e.pratipadika_entry).__name__.endswith("Krdanta"))
                           and to_iast(e.pratipadika_entry.lemma) == model]
                if not entries:
                    continue
                g = gender if gender not in ("pron", "num") else "masc"
                parses = sorted({f"{LINGA.get(_tag(e.linga), g)} {VIBHAKTI.get(_tag(e.vibhakti), '')} {VACANA.get(_tag(e.vacana), '')}" for e in entries})
                if gender == "pron" and stem not in PRONOUNS and not stem.endswith(("eka", "anya", "sarva", "para", "pūrva", "uttara")):
                    continue
                if negated:
                    base_hws = self._direct(negated + ("ḥ" if negated.endswith("a") else "")) or self._direct(negated)
                    pos = base_hws[0].pos if base_hws and base_hws[0].pos in ("adj", "masc", "fem", "nt") else self._noun_pos(negated, [g], g)
                    if "adj" in self._dict_genders(negated):
                        pos = "adj"                                  # agantā: gantṛ is an adjective too, so any gender
                elif abstract:
                    pos = gender
                elif adj_fem or taddhita:
                    stem, pos = (stem[:-1] + "a" if final == "ā" else stem[:-1] if final == "ī" else stem), "adj"   # paścimikāyām, pratyayavatī: feminines
                    if adj_fem or final == "ī":
                        parses = [p for p in parses if p.startswith("fem")]   # pratyayavatī: the feminine alone
                else:
                    pos = "pron" if (stem in PRONOUNS or gender == "pron") else ("card" if gender == "num" else self._noun_pos(stem, [g], g))
                    if stem.endswith("tva") and len(stem) > 5:
                        pos = "nt"                                   # nirapekṣatva: an abstract in -tva is neuter, whatever the dictionaries say
                    elif stem.endswith("tā") and len(stem) > 4 and pos in ("masc", "nt"):
                        pos = "fem"
                if pos == "ind":
                    continue                                         # āśritya: Monier-Williams' ind.p. is the absolutive, not a stem
                bahu = final == "a" and len(self._dictionary_members(stem)) >= 2   # anupādāno: a compound used as an adjective, in any gender
                parses = sorted((p for p in parses if self._gender_ok(stem, [], pos, p.split()[0], loose or bahu)), key=lambda p: _parse_order(p, pos))
                if (negated or abstract) and pos in ("masc", "fem", "nt"):
                    parses = [p for p in parses if p.startswith(pos)]   # amithyātvāt: the neuter, as mithyātva is
                if not parses:
                    continue
                h = self._make_noun(stem, pos, parses, f"{pos}; regular inflection of {stem} (as {model})")
                if taddhita and not h.construction:
                    h.construction = f"{base} + {taddhita}"
                if abstract:
                    base_hws = self._direct(base) if not base.startswith("na + ") else []
                    if base_hws and base_hws[0].construction:
                        base = base_hws[0].construction              # ahetukatā: na + hetuka + tā, as the kosha derives ahetuka
                    h.construction = f"{base} + {abstract}"
                    base_word = base.split(" + ")[-1]
                    h.meaning = h.meaning or ("not " if base.startswith("na + ") else "") + f"the state of being {self._meaning(base_word)[0] or base_word}"
                if negated:
                    base_construction = next((b.construction for b in base_hws if b.stem == negated and b.construction), "")
                    h.construction = f"na + {base_construction or negated}"   # amithyātva: na + mithyā + tva, as the kosha derives mithyātva
                    h.compound_type, h.compound_construction = "negation", f"na + {negated}"
                    h.meaning = h.meaning or "not " + self._meaning(negated)[0]
                self._negation(h)
                out.append(h)
        # one headword per stem, with every model's parses
        seen: dict[str, Headword] = {}
        for h in out:
            if h.stem not in seen:
                seen[h.stem] = h
            else:
                for p in h.parses:
                    if p not in seen[h.stem].parses:
                        seen[h.stem].parses.append(p)
        return sorted(seen.values(), key=lambda h: (self._oblique_agent(h), self._rank(h, key)))

    # -- compounds ----------------------------------------------------------------------------

    @staticmethod
    def _oblique_agent(h: Headword) -> int:
        """adhātuḥ: na + dhātu before the genitive of an agent noun in -ṛ (adhātṛ), as _direct orders dhātuḥ."""
        return 1 if h.stem.endswith("ṛ") and h.parses and all(p.split()[1] in ("gen", "abl") for p in h.parses if len(p.split()) > 1) else 0

    def _nominal(self, stem: str) -> bool:
        """A nominal stem: one vidyut inflects, or a dictionary headword that is not only a verbal root."""
        if stem.endswith(("āt", "asya", "ena", "ebhyaḥ", "ānām")) and stem not in ("vidyut", "marut", "sampat", "anena"):
            return False
        if self.cologne is not None and (self.cologne.is_root(stem) or self.cologne.is_letter(stem)) and stem not in SHORT_MEMBERS:
            return False
        if stem in self.stems or any(v in self.stems for v in nasal_variants(stem)):
            return True
        if stem.endswith("ḥ") and len(stem) > 2:
            return self._nominal(stem[:-1] + "s")
        return (len(stem) >= 3 and self.cologne is not None and self.cologne.known(stem) and not self.cologne.is_root(stem)
                and not self.cologne.is_letter(stem))

    def _weight(self, stem: str) -> int:
        base = (self.cologne.weight(stem) if self.cologne is not None else 0) + (5 if stem in self.stems else 0)
        if stem in DCS_COMMON_LEMMAS or stem in DCS_COMP_MEMBERS:
            base += 3
        return base

    def _verb_of(self, h: Headword) -> str:
        """The verb a participle or absolutive belongs to (prp of utpadyate -> utpadyate), else the lemma."""
        m = re.search(r"\b(?:pp|prp|ptp|abs|inf) of (\S+)", h.grammar or "")
        if m:
            return m.group(1).rstrip(",;")
        first = (h.construction or "").split(" + ")[0]
        return first if first.endswith(("ti", "te")) else h.lemma   # nirudhyate + māna

    @staticmethod
    def _common_verb(verb: str) -> bool:
        """A verb of the common list, also behind a negation (anapekṣate)."""
        return verb in COMMON_VERBS or (verb[:2] == "an" and verb[2:] in COMMON_VERBS) or (verb[:1] == "a" and verb[1:] in COMMON_VERBS)

    def _chance_verb(self, h: Headword) -> bool:
        """A finite verb form that is a chance reading: an imperfect, perfect, aorist or imperative of a verb outside the common
        list (upādān, jara), or a first or second person or a dual of one the dictionaries give no meaning for (avastameva
        as "we two may be stunned", ābhāvaḥ as "we two shine")."""
        if h.pos not in VERB_POS or self._common_verb(h.lemma):
            return False
        if h.pos in RARE_TENSES or h.pos == "imp":
            return True
        return not self._meaning(h.lemma)[0] and not h.lemma.endswith(("ayati", "ayate")) and any(("1st" in x or "2nd" in x or "dual" in x) for x in h.parses)   # not nirvāsyāmi, abhinirvartayāmi

    def _obscure_verbal(self, h: Headword, by_root: bool = False) -> bool:
        """A participle or absolutive of a verb the dictionaries hardly know (avidya as the absolutive of vidayate); with
        ``by_root``, one whose root they do not know either (abhirūḍha of √ruh is then no chance form)."""
        if h.pos not in ("abs", "inf", "pp", "prp", "ptp"):
            return False
        verb = self._verb_of(h)
        root = (h.root or "").lstrip("√")
        if by_root and root and self.cologne is not None and self.cologne.known(root):
            return False
        return (not self._common_verb(verb) and not self._meaning(verb)[0]
                and (self.cologne is None or (self.cologne.weight(h.stem) < 3 and not self.cologne.known(verb))))

    def _solid(self, word: str) -> str:
        """How surely ``word`` stands alone in a sandhi split: 'strong' for a particle, pronoun or finite verb
        (na + avidyā, tasmāt + iti), 'weak' for a noun in a case other than the vocative (śūnyatā + eva), '' for
        a bare stem (citta + āvaraṇa is a compound)."""
        hws, note = self._resolve(word)
        if not hws and self._negated_word(word):
            return "weak"                                            # anirodham: as solid as nirodham
        if not hws and self._good_compound(word):
            return "weak"                                            # cittasaṃtānaḥ: an inflected compound stands like a noun
        if not hws or (note and hws[0].kind not in ("honorific", "name", "technical") and self._weight(hws[0].stem) < 10):
            return ""
        h = hws[0]
        if self._chance_verb(h):
            return "weak"                                            # abhā, avāt, jara, avastameva: a chance form of an obscure root is no particle
        if self._obscure_verbal(h):
            return "weak"                                            # avidya: the absolutive of vidayate is no anchor
        if h.pos in VERB_POS and not self._common_verb(h.lemma):
            return "weak"                                            # āvasati: a present of a verb outside the common list is no anchor
        if h.pos in ("pron", "abs", "inf") or h.pos in VERB_POS or (h.pos == "ind" and (h.stem in INDECLINABLES or h.stem in SHORT_WORDS or h.stem in COMMON)):
            return "strong"
        if h.pos == "ind":
            return "weak"
        if any(not re.search(r"\bvoc\b", p) for h in hws for p in h.parses):
            return "weak"
        return ""

    def _junction_variants(self, left: str, right: str) -> list[tuple[str, str]]:
        """The members a compound junction may hide (Pāṇini's *ac-*, *hal-*, *visarga-sandhi*, *cvi*, *ṇatva* and *ṣatva*):
        ``cittāvaraṇa`` -> citta + āvaraṇa; ``tryadhva`` -> tri + adhva; ``ātmasaṃjñā`` -> ātman + saṃjñā."""
        return compound_junction_variants(left, right)

    def _compound_splits(self, key: str) -> list[list[str]]:
        """Member lists for ``key`` read as a compound of stems the dictionaries know; the last member as it stands."""
        if key in self._comp_splits_cache:
            return self._comp_splits_cache[key]
        if len(key) > 65:
            self._comp_splits_cache[key] = []
            return []
        max_depth = 7 if len(key) >= 30 else 4
        results: list[tuple[int, list[str]]] = []
        dead_rest: set[tuple[str, int]] = set()

        def last_ok(rest: str) -> bool:
            if len(rest) > 22 or (len(rest) < 3 and rest not in SHORT_MEMBERS):
                return False
            hws, _ = self._resolve(rest, loose=True)
            return bool(hws) and not all(h.pos == "ind" or h.pos in VERB_POS or (self.cologne is not None and self.cologne.is_letter(h.stem)) for h in hws)

        def rec(rest: str, acc: list[str], depth: int, cost: int) -> None:
            if len(results) >= 40 or depth > max_depth or (rest, depth) in dead_rest:
                return
            before = len(results)
            if acc and last_ok(rest):
                results.append((cost, acc + [rest]))
                return                                        # a complete reading: do not cut the last member further
            hi = min(len(rest) - 2, 18) if len(rest) > 22 else len(rest) - 2
            for i in range(hi, 0, -1):                        # the longest first member first
                for vi, (left, right) in enumerate(self._junction_variants(rest[:i], rest[i:])):
                    if len(right) < 2 or right == rest:
                        continue                                    # (ā + dhipateya read as a + ādhipateya consumes nothing)
                    if left in ("a", "an") and not acc and (self.stem_known(right) or last_ok(right) or any(self.stem_known(right[:j]) for j in range(3, len(right)))):
                        rec(right, acc + ["na"], depth + 1, cost + (1 if vi else 0))   # the negation at the start of the word only
                    elif (len(left) >= 4 and self._nominal(left)) or (len(left) in (2, 3) and self._short_member(left) and left != "an") or (len(left) == 2 and left in PREFIXES and left != "an"):
                        rec(right, acc + [left], depth + 1, cost + (1 if vi else 0))
            if len(results) == before and len(results) < 40:
                dead_rest.add((rest, depth))

        rec(key, [], 0, 0)
        # fewest members; the junction as written before an altered one; a negation before other readings; long
        # members; members the dictionaries know well
        def poor_last(m: list[str]) -> int:
            """A last member that is only a chance form of a rare stem (ālasamaye) counts as an extra member."""
            last, _ = self._resolve(m[-1], loose=True)
            return 1 if not last or (self._weight(last[0].stem) < 4 and last[0].stem not in NUMERALS) else 0

        def na_first(m: list[str]) -> int:
            if m[0] != "na" or len(m) != 2:
                return 1
            joined = ("an" if m[1][:1] in "aāiīuūṛeo" else "a") + m[1]
            return 2 if any(joined.startswith(t) and len(joined) > len(t) for t in CORE_TERMS if len(t) > 4) else 0   # avidyā-kṣaya

        def last_weight(m: list[str]) -> int:
            """How well the dictionaries know the last member's stem (asura before the chance āsura)."""
            last, _ = self._resolve(m[-1], loose=True)
            return min(self.cologne.weight(last[0].stem), 24) if last and self.cologne is not None else 0

        results.sort(key=lambda cm: (na_first(cm[1]), len(cm[1]) + poor_last(cm[1]),
                                     -sum(min(self._weight(x), 24) for x in cm[1][:-1]), -last_weight(cm[1]), cm[0],
                                     -min(len(x) for x in cm[1] if x != "na")))
        top = [m for _, m in results[:4]]
        self._comp_splits_cache[key] = top
        return top

    def _short_member(self, stem: str) -> bool:
        """A short member: a numeral, a prefix, a known 2–3 letter stem (SHORT_MEMBERS), or a 3-letter word the
        dictionaries treat as a nominal (not a root or alphabet letter)."""
        if stem in NUMERALS or stem in PREFIXES or stem in SHORT_MEMBERS:
            return True
        return (len(stem) == 3 and self.cologne is not None and self.cologne.weight(stem) >= 6
                and not self.cologne.is_letter(stem) and not self.cologne.is_root(stem))

    def _stem_splits(self, stem: str) -> list[str]:
        """A stem the dictionaries do not analyse, read as two stems: ``tryadhva`` -> tri + adhvan."""
        best: tuple[tuple, list[str]] | None = None
        for i in range(len(stem) - 2, 1, -1):
            for left, right in self._junction_variants(stem[:i], stem[i:]):
                left = NUMERAL_SANDHI.get(left, left)
                if left == "na" or len(right) < 3 or left in PREFIXES or not (left in NUMERALS or self._nominal(left)):
                    continue
                if left not in NUMERALS and (self.cologne is None or self.cologne.weight(left) < 4):
                    continue                                        # paś + cimika: not members the dictionaries know
                for r in (right, right + "n"):
                    if not self._nominal(r) or (self.cologne is not None and self.cologne.weight(r) < 4):
                        continue
                    score = (r in self.stems, left in self.stems or left in NUMERALS, self._weight(left) + self._weight(r))
                    if best is None or score > best[0]:
                        best = (score, [left, r])
        return best[1] if best else []

    def _expand_members(self, stems: list[str], depth: int = 0) -> list[str]:
        """Each member by its own members: a negation as ``na + X`` (anutpanna), a dictionary compound by the
        members Monier-Williams marks (svabhāva -> sva + bhāva), a compound the dictionaries do not analyse by
        its stems (tryadhva -> tri + adhvan); names and honorifics stay whole."""
        out: list[str] = []
        for m in stems:
            if m == "na" or depth > 3 or len(m) < 3:
                out.append(m)
                continue
            if m.endswith("o") and len(m) > 3 and self._nominal(m[:-1] + "as") and not self._edgerton_word(m):
                m = m[:-1] + "as"                                    # mano-: the stem manas
            if _classify(m, self._meaning(m)[0]) in ("name", "honorific"):
                out.append(m)
                continue
            rest = "" if m in CORE_TERMS else self._negated_rest(m)  # avidyā, anātman: a term is not split into na + …
            if rest:
                out += ["na"] + self._expand_members([rest], depth + 1)
                continue
            dm = self._dictionary_members(m)
            if dm and dm[0] == "na" and m in CORE_TERMS:
                dm = []                                              # avidyā: Monier-Williams' a-vidyā, but a term
            if dm:
                out += self._expand_members(dm, depth + 1)
                continue
            if m not in self.stems and not (self.cologne is not None and (any(r["source"] == "mw" for r in self.cologne.lookup(m)) or (len(m) < 9 and self.cologne.known(m)))):
                ss = self._stem_splits(m)
                if ss:
                    out += self._expand_members(ss, depth + 1)
                    continue
                if len(m) >= 8:                                      # trisāhasramahāsāhasra: tri + sāhasra + mahā + sāhasra
                    for members in self._compound_splits(m + "ḥ")[:1]:
                        last = self.analyse(members[-1], 1)
                        if last.headwords and len(members) <= 5:
                            firsts = [x if x == "na" else self._member_stem(self.analyse(x, 1)) for x in members[:-1]]   # satva-: sattva
                            out += self._expand_members(firsts + [self._member_stem(last)], depth + 1)
                            break
                    else:
                        out.append(m)
                    continue
            out.append(m)
        return out

    def deconstruct(self, key: str) -> list[str]:
        return [" + ".join(self._expand_members(m[:-1]) + [m[-1]]) for m in self._compound_splits(normalise(key))]

    def _compound_readings(self, key: str) -> tuple[list[Headword], list[Split], str, bool]:
        """Compound readings of the form as written, else of its classical spelling (tṛsāhasramahāsāhasrāṃ):
        (headwords, splits, the note on the reading, whether the junction had to be altered)."""
        first_splits: list[Split] = []
        best: tuple[tuple, list[Headword], list[Split], str, bool] | None = None
        for cand, why in [(key, "")] + readings(key)[:6]:
            comp_hws: list[Headword] = []
            comp_splits: list[Split] = []
            altered = False
            for members in self._compound_splits(cand):
                analyses = [self.analyse(m, 1) for m in members]
                comp_splits.append(Split(members, "compound", analyses))
                if analyses[-1].headwords and not comp_hws:
                    comp_hws.append(self._compound_headword(cand, [self._member_stem(a) for a in analyses[:-1]], analyses))
                    altered = "".join(members).replace("na", "a", 1) != cand if members[0] == "na" else "".join(members) != cand
            if cand == key:
                first_splits = comp_splits
            if comp_hws:
                members = [m for m in (comp_hws[0].compound_construction or "").split(" + ") if m and m != "na"]
                mean = sum(min(self._weight(m), 24) for m in members) / max(1, len(members))
                score = (1 if self._poor_compound(comp_hws[0]) else 0, -mean, 1 if why else 0)
                if best is None or score < best[0]:
                    best = (score, comp_hws, comp_splits, (f"read as {cand} (Edg. {why})" if why else ""), altered)
                if score[0] == 0 and not why and mean >= 8:
                    break                                           # the spelling as written, well read: no need to look further
        if best is not None:
            return best[1], best[2], best[3], best[4]
        return [], first_splits, "", False

    def _merge_prefixes(self, stems: list[str]) -> list[str]:
        """A verbal prefix cut off as a member rejoins the word it belongs to: prati + krānta -> pratikrānta."""
        out: list[str] = []
        for m in stems:
            if out and out[-1] in PREFIXES and out[-1] not in ("na", "a", "an", "sa") and len(out) < len(stems):
                out[-1] = out[-1] + m                                 # (sa "with" stays a member: sa + deva + mānuṣa + asura)
            else:
                out.append(m)
        return out

    def _compound_quality(self, h: Headword) -> int:
        """The dictionaries' weight of the compound's least-known member (na, numerals and prefixes aside)."""
        members = [m for m in (h.compound_construction or "").split(" + ") if m and m != "na" and m not in NUMERALS and m not in PREFIXES]
        return min((self.cologne.weight(m) for m in members), default=0) if self.cologne is not None else 0

    def _pair_quality(self, parts: list[str]) -> int:
        """The dictionaries' weight of the less-known word of a sandhi pair."""
        if self.cologne is None:
            return 0
        weights = []
        for p in parts:
            hws, _ = self._resolve(p)
            base = ""
            if not hws:
                base = self._negation_base(p)
                if base:
                    hws, _ = self._resolve(base)                     # anirodham: as well known as nirodham
            w = self.cologne.weight(hws[0].stem) if hws else 0
            if hws and (hws[0].pos in VERB_POS or hws[0].pos in ("abs", "inf")):
                w = max(w, 10 if self._common_verb(self._verb_of(hws[0])) else 3)   # jāyate: a verb has no dictionary weight of its own
            elif hws:
                members = [m for m in (hws[0].construction or "").split(" + ") if m and m not in ("na", "tva", "tā", "ya", "ika", "ka", "vat", "mat")]
                if members:
                    w = max(w, min(self._weight(m) for m in members))   # anyatvam, śauṣiryam: as well known as its base
                if base and (hws[0].pos in ("abs", "pp", "prp", "ptp") or hws[0].pos in VERB_POS):
                    w = max(w, 5 if self._real_word(base) else 0)      # abhūtvā: as real as bhūtvā
            if not hws and self._good_compound(p):
                w = self._good_info(p)[1]                            # cittasaṃtānaḥ: as well known as its least-known member
            if hws and (hws[0].compound_construction or "").startswith("na + "):
                w = max(w, self.cologne.weight(hws[0].compound_construction.split(" + ")[-1]))   # anutpādam: as well known as utpāda
            weights.append(w)
        return min(weights, default=0)

    def _poor_compound(self, h: Headword) -> bool:
        """A compound reading made of scraps: more than four members (unless every member is a well-known word), or a short
        member that is no numeral, prefix or negation (anāthapiṇḍada + sya + ārāma)."""
        members = [m for m in (h.compound_construction or "").split(" + ") if m]
        too_many = len(members) > 4 and not (len(members) <= 9 and min((self._weight(m) for m in members if m != "na"), default=0) >= 6
                                             and all(self.cologne is None or self.cologne.known(m) for m in members if m != "na"))
        return too_many or any(((len(m) <= 3 and not self._short_member(m))
                                or (self._weight(m) < 5 and m not in CORE_TERMS)
                                or (self.cologne is not None and ((self.cologne.weight(m) < 3 and m not in DCS_COMMON_LEMMAS and m not in DCS_COMP_MEMBERS)
                                                                  or self.cologne.is_root(m) or self.cologne.is_letter(m)) and m not in CORE_TERMS))
                               and m not in NUMERALS and m not in PREFIXES and m not in SHORT_MEMBERS and m not in ("na", "sva") for m in members)   # pratyaya + ādi is sound

    def _member_stem(self, a: Analysis) -> str:
        """The lemma of a non-final compound member from its analysis: the headword spelt like the member (vedanā,
        not vedana), else the first nominal one that begins like it, else the member as written."""
        if a.key in ("na", "sa", "su", "sva") or not a.headwords:
            return a.key
        chosen = ""
        for h in a.headwords:
            if h.stem == a.key and h.pos in NOMINAL_POS:
                chosen = h.stem
                break
        if not chosen:
            for h in a.headwords[:3]:
                if h.pos in NOMINAL_POS and h.stem[:2] == a.key[:2]:
                    chosen = h.stem
                    break
        if chosen and self.cologne is not None and self.cologne.weight(chosen) < 10:   # satva-: sattva, not the rarer satvan
            keys = [a.key] + ([a.key[:-1]] if a.key.endswith("n") and len(a.key) > 4 else [])   # satvan: the an-stem variant of satva
            for k in keys:
                for cand, _ in readings(k)[:4]:
                    better = [h for h in self._direct(cand, loose=True) if h.pos in NOMINAL_POS and h.stem in (cand, cand + "n")]
                    if better and self.cologne.weight(better[0].stem) >= 10 and self.cologne.weight(better[0].stem) > self.cologne.weight(chosen) + 2:
                        return better[0].stem
        return chosen or a.key

    def _compound_headword(self, key: str, members: list[str], analyses: list[Analysis]) -> Headword:
        """One headword for a compound: the non-final members as stems, the last member's inflection, the members
        expanded (negation, dictionary members), a -tva/-tā suffix set apart, a name kept whole."""
        last_hws = analyses[-1].headwords
        last = next((h for h in last_hws if h.pos in NOMINAL_POS or h.pos in ("abs", "inf")), last_hws[0])
        if last.pos in ("abs", "inf"):                                 # tri + pradakṣiṇī + kṛtvā: the verb is the last member
            stems = self._expand_members(members) + [last.lemma]
            tail = analyses[-1].key
            n = next((k for k in range(len(tail), 0, -1) if key.endswith(tail[-k:])), 0)
            shown = key[:len(key) - n] + tail if n else key
            return Headword(id=self._new_id(), lemma=shown, stem=shown, pos=last.pos, grammar=f"{last.pos} of {last.lemma}, comp",
                            meaning="; ".join(f"{m}: {self._meaning(m)[0].split(';')[0][:60]}" for m in stems[:-1]) + f"; {last.lemma}: {last.meaning.split(';')[0][:60]}",
                            meaning_lit="", meaning_2="", construction=" + ".join(stems), root="", root_meaning="", family_set="", plus_case="",
                            compound_type="samāsa", compound_construction=" + ".join(stems), parses=[], kind="")
        suffix, last_stem = "", last.stem
        if (last.pos == "adj" and last_stem.endswith("a") and last.parses and all(p.startswith("fem") for p in last.parses)
                and any(h.pos == "fem" and h.stem == last_stem + "ā" for h in last_hws)):
            last_stem = last_stem + "ā"                              # satvasaṃjñā: the noun saṃjñā, not the adjective -saṃjña
        parts = last.construction.split(" + ") if last.construction else []
        if len(parts) == 2 and parts[1] in ("tva", "tā") and last.pos in ("masc", "fem", "nt"):
            last_stem, suffix = parts[0], parts[1]
        elif last_stem in ("tva", "tā") and members:                  # aprāpti + tvād: the suffix read as a word
            suffix, last_stem = last_stem, ""
        stems = self._merge_prefixes(self._expand_members(members + ([last_stem] if last_stem else [])))
        pos = last.pos if last.pos in NOMINAL_POS else "adj"
        parses = list(last.parses)
        if suffix == "tva":
            pos = "nt"
            parses = [p for p in parses if p.startswith("nt")] or [re.sub(r"^(masc|fem)", "nt", p) for p in parses]
        elif suffix == "tā":
            pos = "fem"
            parses = [p for p in parses if p.startswith("fem")] or parses
        meaning_parts = []
        for m in stems:
            if m == "na":
                meaning_parts.append("na: not")
                continue
            mm, _ = self._meaning(m)
            meaning_parts.append(f"{m}: {mm.split(';')[0][:60]}" if mm else m)
        if suffix:
            meaning_parts.append(f"{suffix}: -ness, the state of being")
        construction = " + ".join(stems) + (f" + {suffix}" if suffix else "")
        if last.pos in ("pp", "prp", "ptp") and last.construction:
            construction = " + ".join(stems) + " + " + last.construction.split(" + ")[-1]
        # the compound's stem as written: the text's own spelling up to the last member, then the last member's stem
        tail = analyses[-1].key
        n = next((k for k in range(len(tail), 0, -1) if key.endswith(tail[-k:])), 0)
        prefix = key[:len(key) - n] if n else key[:max(0, len(key) - len(tail))]
        hidden = len(tail) - n
        shown = prefix + (last_stem[hidden:] if last_stem else "") + suffix
        kind = "name" if last.kind == "name" else ""
        compound_type = "negation" if stems and stems[0] == "na" and len(stems) == 2 else "samāsa"
        if kind == "name" and all(m in NAME_PREFIXES for m in stems[:-1]):   # āryāvalokiteśvara: one name
            construction, compound_type = "", ""
        grammar = (last.grammar.split(";")[0] if last.pos in ("pp", "prp", "ptp") else pos) + (", comp" if compound_type else "")
        return Headword(id=self._new_id(), lemma=shown, stem=shown, pos=pos, grammar=grammar,
                        meaning="; ".join(meaning_parts), meaning_lit="", meaning_2="", construction=construction, root="",
                        root_meaning="", family_set="", plus_case="", compound_type=compound_type,
                        compound_construction=" + ".join(stems) if compound_type else "", parses=parses, kind=kind)

    # -- sandhi between words ----------------------------------------------------------------

    @staticmethod
    def _flatten(parts: list[str]) -> list[str]:
        """nāpi + ahetutaḥ -> na + api + ahetutaḥ: the words run together that the table knows, opened out."""
        out: list[str] = []
        for p in parts:
            out.extend(SANDHI_PAIRS.get(p, [p]))
        return out

    @staticmethod
    def _negation_rests(word: str) -> list[str]:
        """What a word beginning with a or an may negate: anirodha -> nirodha (a + n…) or irodha (an + a vowel)."""
        out: list[str] = []
        if len(word) > 4 and word[1:2] not in "aāiīuūṛeoṃḥ" and not word[1:].startswith("tm"):
            out.append(word[1:])                                     # (atmānam is not a + the Vedic tman)
        if len(word) > 5 and word[1:2] == "n" and word[2:3] in "aāiīuūṛeo":
            out.append(word[2:])
        return out

    def _junk_reading(self, hws: list[Headword]) -> bool:
        """Headwords that are all forms of stems the dictionaries lack and vidyut alone lists (anupāda, mohi), or modelled on
        such stems (anupādi), nothing productive (an abstract or negation of a known word) among them."""
        if not hws or self.cologne is None:
            return False
        for h in hws:
            if self.cologne.known(h.stem) or self.cologne.weight(h.stem) >= 2 or h.pos in VERB_POS or h.pos in ("abs", "pp", "prp", "ptp", "ind", "pron", "card"):
                return False
            members = [m for m in (h.construction or "").split(" + ") if m and m not in ("na", "tva", "tā")]
            if members and all(self.cologne.known(m) and self.cologne.weight(m) >= 2 for m in members):
                return False                                         # anyatva, apunarutpatti: a formation on known words
        return True

    def _negation_base(self, p: str, hws: list[Headword] | None = None) -> str:
        """``anirodham`` -> ``nirodham``: the inflected word a negation the dictionaries lack is built on, else ''."""
        if p[:1] != "a" or len(p) < 6:
            return ""
        own = self._resolve(p)[0] if hws is None else hws
        if own and not self._junk_reading(own):
            return ""                                                # a word in its own right (aśāśvatam) is not this case
        for rest in self._negation_rests(p):
            hws, note = self._resolve(rest)
            if hws and (hws[0].compound_type == "negation" or (hws[0].construction or "").startswith("na + ")):
                continue                                             # an + asādhya: no double negation
            if (len(rest) >= 4 and hws and not note and (self._solid(rest) == "weak" or hws[0].pos == "abs")
                    and (self._weight(hws[0].stem) >= 4 or hws[0].pos in ("abs", "pp", "prp", "ptp") or hws[0].stem in CORE_TERMS)):
                return rest                                          # anupādāya, ajanitaḥ: a negated absolutive or participle too
        return ""

    def _negation_headword(self, key: str, hws: list[Headword] | None = None) -> Headword | None:
        """``abhūtvā``, ``anupādāya``, ``ajanitaḥ``: a negated absolutive or participle the dictionaries lack, as one word."""
        base = self._negation_base(key, hws)
        if not base:
            return None
        bh = self._resolve(base)[0][0]
        if bh.pos not in ("abs", "pp", "prp", "ptp"):
            return None
        suffix = (bh.construction or "").split(" + ")[-1] if bh.construction else ("tvā" if bh.pos == "abs" else "")
        root = bh.lemma if bh.pos == "abs" else bh.stem
        construction = f"na + {root}" + (f" + {suffix}" if suffix and suffix != root else "")
        stem = key[:-1] if bh.pos != "abs" and key.endswith(("ḥ", "ṃ", "m")) else key
        return replace(bh, id=self._new_id(), lemma=stem, stem=stem, grammar=bh.grammar.split(";")[0] + ", comp", construction=construction,
                       compound_type="negation", compound_construction=f"na + {root}", meaning="not " + bh.meaning if bh.meaning else "")

    def _negation_twin(self, p: str) -> bool:
        """``ābhāvaḥ``: whether the same form with a short initial a is a negation of a known word (abhāvaḥ)."""
        twin = "a" + p[1:]
        hws, _ = self._resolve(twin)
        if hws:
            h = hws[0]
            rest = self._negated_rest(h.stem) if h.stem[:1] == "a" and len(h.stem) >= 5 else ""
            return (h.compound_type == "negation" or (h.construction or "").startswith("na + ")
                    or bool(rest and (self._weight(rest) >= 4 or rest in CORE_TERMS)))   # abhāva: a negated term that stays whole
        return self._negated_word(twin)

    def _negated_word(self, p: str) -> bool:
        """``anirodham``: a word the dictionaries have only without its negation, read as na + the word."""
        return bool(self._negation_base(p))

    def _good_compound(self, p: str) -> bool:
        """``cittasaṃtānaḥ`` in ``cittasaṃtānaścetasaḥ``: an inflected compound of words the dictionaries know, which stands
        in a sandhi chain like a word."""
        return self._good_info(p) is not None

    def _surface_weight(self, surface: str, a: Analysis) -> int:
        """How well the dictionaries know a compound member as written (upādāna, not its pieces upā + dāna)."""
        w = max(self.cologne.weight(c) for c in [surface] + list(nasal_variants(surface)))
        nominal = [h for h in a.headwords if "BHS" not in h.grammar and h.pos not in VERB_POS]
        if nominal:
            h = nominal[0]
            w = max(w, self.cologne.weight(h.stem), 6 if h.stem in CORE_TERMS or h.stem in DCS_COMMON_LEMMAS or h.stem in DCS_COMP_MEMBERS else 0)
            if h.compound_type == "negation" or (h.construction or "").startswith("na + "):
                base = [m for m in h.construction.split(" + ") if m and m != "na"]
                if base:
                    w = max(w, self.cologne.weight(base[0]))         # ananya: as well known as anya
            if h.compound_construction:
                w = max(w, self._compound_quality(h))
        if w < 6 and len(surface) >= 7:
            info = self._good_info(surface, resolved_too=True, bare=True)   # parātmānau: para + ātman; uttamādhama: uttama + adhama
            if info is not None:
                w = max(w, info[1])
        return w

    def _good_info(self, p: str, resolved_too: bool = False, bare: bool = False) -> tuple[int, int] | None:
        """(members, the least-known member's weight) of ``p`` read as a sound compound, else None: two to four members,
        none a scrap (etan + nā, asac + cā) and none ending in a visarga (cittasaṃtānaḥ + cetaso is two words), the last
        a nominal (avidyānivṛtas + tridhā is not), all of them words the dictionaries know. A form the dictionaries read
        as one word (madhvān) is not this case unless ``resolved_too``."""
        ck = f"{p}\x01{int(resolved_too)}{int(bare)}"
        if ck in self._good_cache:
            return self._good_cache[ck]
        self._good_cache[ck] = None
        if len(p) < 6 or len(p) > 50 or self.cologne is None or (not resolved_too and self._resolve(p)[0]):
            return None
        comp_hws, comp_splits, note, _ = self._compound_readings(p)
        if not comp_hws or note:
            return None
        h = comp_hws[0]
        split = next((s for s in comp_splits if s.analyses and s.analyses[-1].headwords), None)
        max_parts = 8 if len(p) >= 28 else 4
        if split is None or not 2 <= len(split.parts) <= max_parts or (len(split.parts[-1]) < 4 and not split.parts[-1].startswith("ād")):
            return None                                              # madhu + ān is no compound; śāśvatāśāśvata + ādi is
        if split.parts[0] in ("a", "an", "na") and ((len(split.parts) == 2 and (len(split.parts[1]) < 7 or self._resolve(split.parts[1])[0]))
                                                     or split.parts[1] in PREFIX_SURFACES or len(split.parts[1]) < 4):
            return None                                              # antavā as an + tavā, āprasiddhi as a + aprasiddhi, a + api + …: negations are read elsewhere
        if split.parts[-1] == "ādi":
            h = replace(h, pos="masc", parses=h.parses or ["masc nom sg", "nt nom sg", "nt acc sg"])   # śāśvatāśāśvatādi: ādi as a bare stem
        if not h.parses or (h.pos == "pron" and h.stem in PRONOUNS) or (h.pos not in NOMINAL_POS and not any(x.pos in NOMINAL_POS for x in split.analyses[-1].headwords)):
            return None                                              # avidyānivṛtas + tridhā: an adverb is no last member (prabhṛti is also a noun); amiti + etat
        last = next((x for x in split.analyses[-1].headwords if x.pos in NOMINAL_POS), split.analyses[-1].headwords[0])
        dg_all = self._dict_genders(last.stem)
        dg = dg_all & {"masc", "fem", "nt"}
        if dg and "adj" not in dg_all and "fem" not in dg and last.stem.endswith("a") and all(x.startswith("fem") for x in h.parses):
            return None                                              # anya + annā: anna is neuter, so no feminine annā ends a compound
        if split.analyses[-1].headwords and split.analyses[-1].headwords[0].pos in VERB_POS:
            return None                                              # nābha + avāj + jāyate: a verb ends no compound
        if not bare and all("voc" in x for x in h.parses) and split.parts[-1][-1:] not in "iu":
            return None                                              # jarāmaraṇadharma + eṣu: a bare stem is no word before eṣu (ādi may be a neuter)
        weights: list[int] = []
        pieces = 0
        for i, (surface, a) in enumerate(zip(split.parts, split.analyses)):
            if i > 0 and (surface[:1] in "ṃḥṅñṇ" or (surface[:1] in "rl" and surface[1:2] not in VOWELS)):
                return None                                          # saṃtati + rnaḥ: no word begins so
            pieces += 1
            if i < len(split.parts) - 1:
                if surface in ("na", "a", "an", "antaḥ", "bahiḥ", "adhaḥ", "puraḥ", "tiraḥ") or surface in SHORT_MEMBERS or surface in PREFIX_SURFACES or surface in NUMERALS or surface in NUMERAL_SANDHI:
                    continue
                if len(surface) < 4 or surface.endswith("ḥ") or (surface.endswith("s") and split.parts[i + 1][:1] in "tcṭ"):
                    return None                                      # kārakas + tasmā: a visarga ends no member
                if a.headwords and a.headwords[0].pos == "pron" and a.headwords[0].stem != surface and surface not in SHORT_MEMBERS:
                    return None                                      # iyam + ātmānam: an inflected pronoun is no member
                if a.headwords and a.headwords[0].pos == "ind" and (a.headwords[0].stem.endswith("tas") or a.headwords[0].stem in NON_MEMBER_PARTICLES):
                    return None                                      # sa + nipa + atas + tri: an adverb in -tas or a particle is no member
                if (a.headwords and a.headwords[0].pos in ("abs", "inf") and surface not in CORE_TERMS
                        and not (surface == "pratītya" and split.parts[i + 1].startswith("samutp"))
                        and (self._common_verb(self._verb_of(a.headwords[0])) or not any(h.pos in NOMINAL_POS for h in a.headwords))):
                    return None                                      # apekṣya + agniḥ: an absolutive is no member (pratītya-samutpanna is a term; ananya is an adjective)
            weights.append(self._surface_weight(surface, a))
        if not weights or min(weights) < 3 or sum(weights) / len(weights) < 4:
            return None                                              # aṅkura + prabhṛti (5, 4), dīpa + arcis (5, 3) are sound
        if len(weights) == 1 and all(x in PREFIX_SURFACES and x not in ("a", "an", "su", "sa") for x in split.parts[:-1]):
            return None                                              # ā + prasiddhi: a verbal prefix alone makes no compound
        if h.stem in CORE_TERMS or self.cologne.known(h.stem):
            pieces = 1                                               # jarāmaraṇa, nāmarūpa: a compound the dictionaries list is one word
        info = (pieces, min(weights))
        self._good_cache[ck] = info
        return info

    def _sandhi_split(self, parts: list[str]) -> Split:
        """A split into words; a part that is itself two words run together (nāpi in nāpyahetutaḥ) is opened out."""
        flat: list[str] = []
        for p in parts:
            a = self.analyse(p, 0)
            if not a.headwords and a.splits and a.splits[0].source == "sandhi" and a.splits[0].complete:
                flat.extend(a.splits[0].parts)
            else:
                flat.append(p)
        return Split(flat, "sandhi", [self.analyse(p, 0) for p in flat])

    def _plain_word(self, p: str) -> bool:
        """A form the kosha or the dictionaries give as it stands (tathāgatāya, arhate), not one modelled on a stem they
        lack (acaryāṃ as na + caryā)."""
        hws, note = self._resolve(p)
        return bool(hws) and not note and "BHS" not in hws[0].grammar and not ("regular inflection" in hws[0].grammar and not self.cologne.known(hws[0].stem))

    def _real_word(self, p: str) -> bool:
        """A form of a dictionary headword, however rare (anekārtham), or of a negation of one (anānārtham, abhūtvā)."""
        hws, note = self._resolve(p)
        if not hws and not note:
            base = self._negation_base(p)
            return bool(base) and self._real_word(base)
        if not hws or note:
            return False
        h = hws[0]
        if self.real_stem(h.stem) or (h.compound_type == "negation" and self.real_stem(h.compound_construction.split(" + ")[-1])):
            return True
        members = [m for m in (h.construction or "").split(" + ") if m and m not in ("na", "tva", "tā", "ya", "ika", "ka", "vat", "mat")]
        if members and all(self.real_stem(m) for m in members):
            return True                                              # anyatvam: anya + tva; śauṣiryam: śauṣira + ya
        if h.pos in VERB_POS or h.pos in ("pp", "prp", "ptp", "abs", "inf"):
            root = (h.root or "").lstrip("√")
            return bool(h.meaning) or (bool(root) and self.cologne is not None and self.cologne.known(root))   # tiṣṭhan: of √sthā
        return False

    def _word_part(self, p: str) -> bool:
        """A part of a sandhi split must be a word: four letters, a known short word, or a three-letter word the
        dictionaries know well (not anā, the Vedic particle)."""
        if len(p) < 2 or (p in PREFIXES and p not in SHORT_WORDS):
            return False                                             # dur, nis: a prefix is no word; ā, u: no one-letter word in a split
        if p in SHORT_WORDS:
            return True
        if len(p) <= 6:
            hws, _ = self._resolve(p)
            if hws and hws[0].pos == "ind" and hws[0].stem in PREFIXES and hws[0].stem != p:
                return False                                         # pratī: the prefix prati read through a variant
        if len(p) >= 5:
            return True
        if len(p) < 3:
            return False
        hws, _ = self._resolve(p)
        if not hws or (hws[0].pos == "ind" and hws[0].stem != p and hws[0].stem not in INDECLINABLES) or (hws[0].pos == "ind" and hws[0].stem in PREFIXES):
            return False                                             # īni, anām: a scrap the kosha reads as the particle ī, ā; pratī: the prefix prati
        if (hws[0].pos == "ind" and hws[0].stem in INDECLINABLES) or any(h.pos == "card" or h.stem in NUMERALS for h in hws[:3]):
            return True                                              # ṛte, cet, ṣaṭ
        return len(p) == 4 or (self.cologne is not None and self.cologne.weight(hws[0].stem) >= 4)

    def _sandhi_splits(self, key: str, depth: int = 0) -> list[list[str]]:
        """Words written as one: ``utthāyāsanād`` -> utthāya + āsanād, ``nāvidyā`` -> na + avidyā, ``śūnyataiva`` ->
        śūnyatā + eva, ``nātmasaṃjñā`` -> na + the compound, ``acintyenātulyenāmāpyena`` -> a chain of three."""
        ck = f"{key}\x01{int(depth == 0)}"
        if ck in self._sandhi_cache:
            return self._sandhi_cache[ck]
        out: list[list[str]] = []
        for i in range(1, min(len(key) - 1, 26)):
            ch = key[i]
            cands = external_sandhi_cands(key, i)
            consonant = ch not in "aāiīuūeo"                        # parān + ugrāhakaṃ: a junction that is also what a compound looks like
            for left, right in cands:
                if not (self._word_part(left) and self._word_part(right)):
                    continue
                lh, _ = self._resolve(left)
                lh_nonvoc = [x for x in lh if "visarga lost" not in (x.grammar or "")
                             and (not x.parses or x.kind in ("name", "honorific") or not all("voc" in y for y in x.parses))]
                left_ok = (bool(lh_nonvoc) or (depth == 0 and right in PARTICLE_RIGHT and len(left) >= 5 and bool(self.analyse(left, 0).headwords))
                           or self._negated_word(left) or self._good_compound(left))
                if not left_ok:
                    continue
                rh, _ = self._resolve(right)
                parts: list[str] | None = None
                if rh or self._negated_word(right) or self._good_compound(right):
                    parts = [left, right]                              # anirodham + anutpādam: words the dictionaries give only unnegated;
                if len(right) >= 4 and depth < 12 and not (rh and self._plain_word(right)):   # cittasaṃtānaḥ + cetasaḥ: a compound in a chain
                    if (parts is None and (depth == 0 or left in SHORT_WORDS) and not consonant and lh and lh[0].pos in ("ind", "pron", "abs", "inf")):
                        right_hws = self.analyse(right, 0).headwords
                        if right_hws and (self._good_info(right) is not None or not self._poor_compound(right_hws[0])):
                            parts = [left, right]                      # na + a compound (nātmasaṃjñā, nāvidyākṣayo); śrutvā + a verb
                    sub = self._sandhi_splits(right, depth + 1)         # a chain: acintyena + atulyena + …, anirodham + anutpādam + …;
                    for s in sub[:3]:                                  # beside a compound reading of the remainder, the scoring deciding
                        if [left] + s not in out:
                            out.append([left] + s)
                if parts and parts not in out:
                    out.append(parts)
        strength = {"strong": 2, "weak": 1, "": 0}

        def part(p: str, last: bool = True) -> tuple[int, int, int, int, int]:
            """(a word?, a chance reading?, its pieces, a particle, pronoun or absolutive?, the dictionaries' weight of what it is)."""
            hws, note = self._resolve(p)
            weight = self.cologne.weight if self.cologne is not None else (lambda s: 0)
            if hws and not last and "visarga lost" in (hws[0].grammar or ""):
                hws = [x for x in hws if "visarga lost" not in (x.grammar or "") and x.parses and not all("voc" in y for y in x.parses)]
                if not hws:                                          # asatya + eva: a nominative with its visarga lost stands before a
                    return 0, 1, 1, 0, 0                               # space, never joined to the next word (asati + eva is the split)
            if hws:
                h = hws[0]
                members = [m for m in (h.construction or "").split(" + ") if m and m not in ("na", "tva", "tā", "ya", "ika", "ka", "vat", "mat")]
                # duravagāhatā, apunarutpatti, śauṣiryam: an abstract, taddhita or negation of a dictionary word is a productive formation
                productive = (h.compound_type == "negation" or (len(members) == 1 and self._nominal(members[0])
                              and (h.construction.endswith((" + tva", " + tā", " + ya", " + ika", " + vat", " + mat")) or h.construction.startswith("na + "))))
                modelled = "regular inflection" in h.grammar and not self.cologne.known(h.stem)
                if modelled and (not members or (not productive and any(self._weight(m) < 4 for m in members))):
                    info = self._good_info(p)                          # utpādasthitibhaṅgānām: a compound stem vidyut lists
                    if info is not None:
                        members, q = info
                        return 1, 1 if q < 3 else 0, members, 0, q
                    return 0, 1, 1, 0, 0                               # nāsīn: an inflection of a stem the dictionaries lack is no word
                if h.pos in VERB_POS or h.pos in ("abs", "inf", "pp", "prp", "ptp"):
                    w = max(weight(h.stem), 10 if self._common_verb(self._verb_of(h)) else 3)   # abhūm: as well known as bhavati; not its suffix māna
                else:
                    w = max([weight(h.stem)] + [weight(m) for m in (h.construction or "").split(" + ") if m and m != "na"])   # apunarutpatti: as punarutpatti
                if h.parses and all("voc" in x for x in h.parses) and h.kind not in ("name", "honorific"):
                    return 0, 1, 1, 0, 0                               # ekatva + ādīn: a vocative alone in a chain is no word
                rare_verb = self._chance_verb(h)                      # upādān, jara, avastameva: a chance form of an obscure root
                chance = 1 if (note or "BHS" in h.grammar or rare_verb or (modelled and not productive)   # saru, anyannā
                               or (h.pos in ("masc", "fem", "nt", "adj") and w == 0 and not self.cologne.known(h.stem) and h.stem not in CORE_TERMS)) else 0
                return 1, chance, 1, 1 if h.pos == "ind" or p in IRREGULAR_VERBS else 0, w   # nāsi: a chance noun; tāvat, na, abhūm: the anchors
            if self._negated_word(p):
                q = self._pair_quality([p])
                return 1, 1 if q < 2 else 0, 1, 0, q
            info = self._good_info(p)
            if info is not None:
                members, q = info                                      # avidyākṣayo: a compound of known words is a word
                return 1, 1 if q < 3 else 0, members, 0, q
            return 0, 1, 1, 0, 0

        def score(parts: list[str]) -> tuple:
            info = [part(p, k == len(parts) - 1) for k, p in enumerate(parts)]
            whole = all(i[0] for i in info)                          # every part a word: nāpi + ahetutaḥ before na + a scrap
            # then the fewest chance readings (ca + upādānam + eva + ātmā before copāt + ānameva + ātmā), the fewest pieces, a particle
            # counting for half (tathāgatāya + arhate before tathā + agatāya + arhate; cittasaṃtānaḥ + cetaso before the four-member
            # compound; tasmāt + na + atra before tasmāt + nātrā), the most particles (tāvat + na + apratyayāḥ before tau + annāpratyayāḥ),
            # the fewest parts, a negation before its ā- twin, the strongest words
            long_initials = sum(1 for p in parts[1:] if p[:1] in "āīū")   # na + abhūm before na + ābhūm, ca + abuddhaḥ before ca + ābuddhaḥ
            no_avagraha = sum(1 for k in range(len(parts) - 1) if parts[k].endswith("aḥ") and parts[k + 1][:1] == "a")   # sādhanaḥ + apāyāḥ: the text writes its avagrahas
            neg_twins = sum(1 for p in parts[1:] if p[:1] == "ā" and self._negation_twin(p))   # na + ābhāvaḥ: abhāvaḥ, the negation, is meant
            particles = sum(i[3] for i in info)
            return (0 if whole else 1, sum(i[1] for i in info) + no_avagraha, 2 * sum(i[2] for i in info) - particles, -particles, len(parts),
                    neg_twins, -sum(strength[self._solid(p)] for p in parts), -sum(i[4] for i in info), long_initials)   # apekṣya before apekṣyā, tayā before taya

        out.sort(key=score)
        if os.environ.get("KAVI_DEBUG_SPLITS"):
            for parts in out[:6]:
                print(f"  splits({key}, {depth}): {parts} {score(parts)} parts={[part(p, k == len(parts) - 1) for k, p in enumerate(parts)]}", file=sys.stderr)
        # lakṣaṇāni + iti and lakṣaṇānī + iti: the short vowel unless the long one is a word by itself
        keep: list[list[str]] = []
        for parts in out:
            twin = [parts[0][:-1] + "ī" if parts[0].endswith("i") else parts[0][:-1] + "i" if parts[0].endswith("ī") else ""] + parts[1:]
            twin_hws, _ = self._resolve(parts[0])
            if parts[0].endswith("ī") and twin in out and not (twin_hws and self._weight(twin_hws[0].stem) >= 4 and twin_hws[0].stem[-1:] in "īn"):
                continue                                             # nāpī: the kosha's stem nāpi is no word; pratī is prati
            keep.append(parts)
        top = keep[:3]
        self._sandhi_cache[ck] = top
        return top

    # -- the interface ----------------------------------------------------------------------

    def known(self, key: str) -> bool:
        key = normalise(key)
        return self.analyse(key).found or self.stem_known(key)

    def frequency(self, key: str) -> float:
        key = normalise(key)
        return 50.0 if key in INDECLINABLES else (5.0 if self.known(key) else 0.0)

    def headwords_by_lemma(self, stem: str) -> list[int]:
        return [1] if self.stem_known(normalise(stem)) else []

    def root(self, key: str):
        return None

    def lookup(self, key: str):
        return None

    def analyse(self, surface: str, depth: int = 0, mid_capital: bool = False) -> Analysis:
        key = normalise(surface)
        cache_key = f"{key}\x00{mid_capital}\x00{depth}"
        if cache_key in self._analysis:
            return self._analysis[cache_key]
        res = Analysis(surface=surface, key=key, capitalised=mid_capital)
        if not key:
            return res
        if depth == 0 and any(c in key for c in "’‘'") and key[:1] not in "’‘'":
            raw_parts = [p for p in re.split(r"[’‘']+", key) if p]
            av_parts = [raw_parts[0]] + ["a" + p for p in raw_parts[1:]]   # saddharmo’pi, te’ṣṭau: the avagraha marks an elided a
            if len(av_parts) >= 2 and all(len(p) >= 2 for p in av_parts):
                res.splits.append(self._sandhi_split(av_parts))
                res.found = True
                self._analysis[cache_key] = res
                return res
        if key in SANDHI_PAIRS and depth == 0:
            parts = SANDHI_PAIRS[key]
            res.splits.append(self._sandhi_split(parts))
            res.found = True
            self._analysis[cache_key] = res
            return res
        if key.startswith("cch") and len(key) > 5 and not self._direct(key):   # bhāṣyamāṇāṃ cchrutvābhi…: ś written cch after ṃ
            res = replace(self.analyse("ś" + key[3:], depth, mid_capital), surface=surface, key=key)
            res.note = ("initial ś written cch after ṃ" + ("; " + res.note if res.note else ""))
            self._analysis[cache_key] = res
            return res
        # a hyphenated compound: the members are given
        if "-" in surface.strip("-") and depth == 0:
            members = [normalise(m) for m in surface.split("-") if normalise(m)]
            if len(members) >= 2 and any(len(m) == 1 and m not in "aāiīuū" for m in members):
                words = [m for m in members if len(m) > 1]           # vidikṣu-r-avidikṣu: a hiatus-bridging consonant (Edg. § 4.59–65)
                analyses = [self.analyse(m, 0) for m in words]
                res.splits.append(Split(words, "sandhi", analyses))
                res.note = "hiatus-bridging consonant between two words (Edg. §§ 4.59–65)"
                res.found = any(a.found for a in analyses)
                self._analysis[cache_key] = res
                return res
            if len(members) >= 2:
                analyses = [self.analyse(m, 1) for m in members]
                is_comp = (analyses[-1].headwords and analyses[-1].headwords[0].pos != "pron"
                           and all((a.headwords and a.headwords[0].pos not in VERB_POS and a.headwords[0].pos not in ("ind", "pron"))
                                   or (not a.headwords and self.stem_known(a.key)) for a in analyses[:-1]))
                if is_comp:
                    res.splits.append(Split(members, "hyphen", analyses))
                    res.headwords = [self._compound_headword(key.replace("-", ""), [self._member_stem(a) for a in analyses[:-1]], analyses)]
                    res.found = True
                    self._analysis[cache_key] = res
                    return res
                # Em-dash written as hyphen between words or sandhi chains (mahāsattvametadavocat-adyātra, tadyathā-samyagdṛṣṭiḥ)
                res.splits.append(self._sandhi_split(members))
                res.found = any(a.found for a in res.splits[0].analyses)
                self._analysis[cache_key] = res
                return res
        hws, note = self._resolve(key, loose=depth >= 1)
        if not hws and not note:
            neg = self._negation_headword(key, [])
            if neg is not None:
                hws = [neg]                                          # abhūtvā, ajanitaḥ: na + a verb form, one word
        if note:
            res.note = note
        if hws and depth == 0 and hws[0].compound_construction and key.endswith(("ā", "āṃ", "ām", "āyāḥ", "āyai", "āyām", "āyāṃ")):
            last = hws[0].compound_construction.split(" + ")[-1]
            noun = last[:-1] + "ā"
            if last.endswith("a") and any(v in CORE_TERMS for v in [noun] + nasal_variants(noun)):   # jīvasaṃjñā: the noun saṃjñā, not the adjective saṃjña
                for members in self._compound_splits(key)[:1]:
                    analyses = [self.analyse(m, 1) for m in members]
                    if analyses[-1].headwords and analyses[-1].headwords[0].stem in [noun] + nasal_variants(noun):
                        hws = [self._compound_headword(key, [self._member_stem(a) for a in analyses[:-1]], analyses)] + hws
        if hws and mid_capital and self.cologne is not None:         # Subhūtir: a capital in the sentence marks a name
            hws = [replace(h, kind="name", construction="", compound_type="", compound_construction="", grammar=h.grammar.replace(", comp", ""))
                   if h.kind in ("", "name") and self.cologne.has_name(h.stem) else h for h in hws]
            hws = sorted(hws, key=lambda h: 0 if h.kind == "name" else 1)
        if hws:
            res.found = True
            res.headwords = hws
        names_only = bool(hws) and not res.note and all(h.kind == "name" or (h.pos == "adj" and not self.real_stem(h.stem) and not h.construction) for h in hws)
        weak_hits = (bool(hws) and not res.note and self.cologne is not None
                     and all(h.pos in NOMINAL_POS and h.pos != "pron" and not h.compound_construction   # kācit: the indefinite is a reading, not a chance form
                             and h.pos not in ("pp", "prp", "ptp")                 # abhirūḍhaḥ: a participle is no chance form of a stem
                             and ("regular inflection" not in h.grammar or not self.cologne.known(h.stem))   # nāsīn: nāsi, a stem the dictionaries lack
                             and self.cologne.weight(h.stem) < 3 for h in hws))
        # a reading that only a hybrid rule could give, of a stem the dictionaries lack (śrutvābhiśraddadhāsyat), is no better
        # than nothing when the word splits into words that stand on their own (śrutvā + abhiśraddadhāsyanti)
        read_scraps = bool(hws) and bool(res.note) and self.cologne is not None and all(self.cologne.weight(h.stem) < 4 for h in hws)
        weak_hits = weak_hits or read_scraps
        if depth == 0 and hws and not res.note and hws[0].compound_construction and hws[0].compound_type != "negation":
            members = [m for m in hws[0].compound_construction.split(" + ") if m and m != "na"]
            if self._weight(hws[0].stem) < 4 and members and all(self._weight(m) < 4 for m in members):
                weak_hits = True                                     # a compound of stems the dictionaries lack: no better than nothing
        if depth == 0 and key.startswith("nā") and len(key) > 5 and key[2] not in "aāiīuūeoṃḥ" and not self._direct(key):
            alt = "a" + key[2:]                                      # nāpratyayavatī, nākriyāvantaḥ: na + a negated word, not nā-
            if self._resolve(alt)[0] or self._negated_word(alt):
                res.headwords = []
                res.splits = [self._sandhi_split(["na", alt])]
                res.found = True
                self._analysis[cache_key] = res
                return res
        if depth == 0 and (not hws or names_only or weak_hits):
            sandhi_all = []
            for s in (self._flatten(s) for s in self._sandhi_splits(key)):
                if s not in sandhi_all:
                    sandhi_all.append(s)
            # a chain of three or more words (acintyenātulyenāmāpyena, na + api + ahetutaḥ) only when every part is a
            # particle, pronoun or verb, or a word the dictionaries know
            sandhi = [s for s in sandhi_all if len(s) == 2 or all(self._solid(p) == "strong" or self._pair_quality([p]) >= 3 or self._real_word(p) for p in s)]
            # two words joined by sandhi, when the first stands alone as a particle, pronoun or verb (na + avidyā)
            # or the second is a particle (śūnyatā + eva): not a compound
            sure = [s for s in sandhi if (self._solid(s[0]) == "strong" and (len(s) == 2 or all(self._solid(p) == "strong" for p in s[1:])))
                    or (len(s) == 2 and self._solid(s[0]) and self._solid(s[1]) == "strong" and 2 <= len(s[1]) <= 4)   # not ṛddhisaṃpat + ā
                    or (len(s) == 2 and s[1] in PARTICLE_RIGHT and not self._resolve(s[0])[0] and bool(self.analyse(s[0], 0).headwords))]   # a compound + iti
            pair = [s for s in sandhi if all(self._solid(p) for p in s)]   # two words, or a chain of them (hetur + ārambaṇam + anantaram)
            if os.environ.get("KAVI_DEBUG_SPLITS"):
                print(f"  analyse({key}): hws={[h.stem for h in hws[:2]]} weak={weak_hits} names={names_only} sandhi={sandhi} sure={sure} pair={pair}", file=sys.stderr)
            if sure and not hws and len(key) >= 5 and all(self._pair_quality(s) < 4 for s in sure):
                # adhātuḥ: na + dhātu before adha + ātuḥ; sadevamānuṣāsurasya: sa + deva + mānuṣa + asura before sadā + iva…:
                # a compound of well-known words before two chance words that happen to be a particle and a verb
                comp_first, _, _, _ = self._compound_readings(key)
                if comp_first and self._compound_quality(comp_first[0]) >= 8:
                    sure = []
            if sure and sandhi and sandhi[0] not in sure:
                sure = []                                            # tāvat + na + apratyayāḥ ranks above the sure tau + annāpratyayāḥ
            if sure and (not hws or weak_hits):
                if weak_hits:
                    res.headwords = []                                 # yāsāv: yā + asau, not the dual of a rare yāsa
                for parts in sure:
                    res.splits.append(self._sandhi_split(parts))
            elif not hws or names_only:
                comp_hws, comp_splits, comp_note, altered = self._compound_readings(key)
                poor = bool(comp_hws) and self._poor_compound(comp_hws[0]) and self._good_info(key) is None   # upādānamahāgrahaḥ: sound as written
                # anāthapiṇḍadasyārāme, tathāgatāyārhate: two inflected words, when they are better words than the
                # compound's members (a compound of an epithet and a name, āryāvalokiteśvara, is kept)
                comp_size = len([m for m in (comp_hws[0].compound_construction or "").split(" + ") if m]) if comp_hws else 0
                if comp_hws and self._good_info(key) is not None:
                    comp_size = self._good_info(key)[0]               # bhāva + abhāva: two members, not bhāva + na + bhāva
                pq, cq = (self._pair_quality(pair[0]), self._compound_quality(comp_hws[0])) if pair and comp_hws else (0, 0)
                if comp_hws:
                    cq = max(cq, (self._good_info(key) or (0, 0))[1])   # anupādāna: as sound as upādāna, not as upā + dāna
                # prajñāpāramitācaryāṃ: a pair with a compound in it (prajñāpāramitā + caryāṃ) cuts the compound itself, and wins only when that is poor
                oblique_split = len(pair[0]) == 2 and pair[0][0].endswith(("āt", "asya", "ena", "ebhyaḥ", "ānām")) and comp_size >= 4 if pair else False
                simple = (bool(pair) and (all(self._plain_word(p) for p in pair[0]) or oblique_split) and not self._negated_word(key)
                          and not any(pair[0][k].endswith("aḥ") and pair[0][k + 1][:1] == "a" for k in range(len(pair[0]) - 1)))   # sādhano'pāyāḥ would be written
                if os.environ.get("KAVI_DEBUG_SPLITS"):
                    print(f"  pair-vs-compound({key}): comp={[(h.stem, h.compound_construction, h.kind) for h in comp_hws[:1]]} poor={poor} simple={simple} pq={pq} cq={cq} size={comp_size}", file=sys.stderr)
                if pair and not hws and comp_hws and comp_hws[0].kind != "name" and (poor or (simple and (pq > cq or (pq == cq and len(pair[0]) < comp_size)))):
                    for parts in pair:
                        res.splits.append(self._sandhi_split(parts))
                    res.splits += comp_splits
                elif pair and not hws and not comp_hws:
                    for parts in pair:
                        res.splits.append(self._sandhi_split(parts))
                    res.splits += comp_splits
                else:
                    res.splits += comp_splits
                    if comp_hws and (not res.headwords or names_only):
                        comp = comp_hws[0]
                        if comp_note and not res.note:
                            res.note = comp_note
                        edgerton_name = any(h.kind == "name" and self._edgerton_name(h.stem) for h in hws)
                        comp_members = [m for m in (comp.compound_construction or "").split(" + ") if m]
                        epithet = (not mid_capital and len(comp_members) >= 3 and comp_members[0] != "na"   # anāthapiṇḍada is a name, not na + nātha + …
                                   and all(self._weight(m) >= 5 or m in NUMERALS or m == "na" for m in comp_members))
                        if names_only and (mid_capital or comp.kind == "name" or (edgerton_name and not epithet)):
                            res.headwords = res.headwords + [comp]      # Śāriputra: the name, then śāri + putra
                        else:
                            res.headwords = [comp] + res.headwords
                    for parts in sandhi:
                        res.splits.append(self._sandhi_split(parts))
            if not res.headwords and not res.splits:
                for cand, why in readings(key)[:6]:                    # a hybrid spelling of words run together
                    sandhi = self._sandhi_splits(cand)
                    if sandhi:
                        res.splits += [self._sandhi_split(parts) for parts in sandhi]
                        res.note = f"read as {cand} (Edg. {why})"
                        break
                if not res.splits and key[:2] in ("na", "ca") and len(key) >= 5 and key[2] not in "aāiīuūeoṃḥ":
                    alt = "a" + key[2:]                                 # nabhilapyaḥ, casau: na + abhilapyaḥ, ca + asau with the a dropped
                    if self._resolve(alt)[0] or self.analyse(alt, 0).headwords:
                        res.splits.append(Split([key[:2], alt], "sandhi", [self.analyse(key[:2], 0), self.analyse(alt, 0)]))
                        res.note = f"{key[:2]} + a-, the a dropped in the hiatus"
            if res.splits:
                res.found = True
        if mid_capital and not res.headwords and not any(s.complete for s in res.splits):
            res.name_hint = True
        self._analysis[cache_key] = res
        return res


# ------------------------------------------------------------------------------------------
# What to leave in Sanskrit
# ------------------------------------------------------------------------------------------

DUAL_FORMS = {"dve": ["fem nom dual", "nt nom dual", "fem acc dual", "nt acc dual"], "ubhe": ["fem nom dual", "nt nom dual", "fem acc dual", "nt acc dual"]}
HONORIFICS = {"bhagavat", "bhagavant", "bhagavān", "āyuṣmat", "āyuṣmant", "āyuṣman", "bhadanta", "bhadra", "bho", "bhavat", "bhavant",
              "tathāgata", "arhat", "arhant", "samyaksaṃbuddha", "samyaksambuddha", "buddha", "sugata", "jina", "śāstṛ", "śāstar",
              "bhikṣu", "bhikṣuṇī", "śrāmaṇera", "upāsaka", "upāsikā", "śramaṇa", "brāhmaṇa", "parivrājaka", "bodhisattva", "mahāsattva",
              "śrāvaka", "deva", "mahārāja", "ācārya", "upādhyāya", "sthavira", "mahāsthavira", "ārya"}
CAPITALISED = {"bhagavat", "bhagavant", "bhagavān", "tathāgata", "sugata", "samyaksaṃbuddha", "samyaksambuddha", "buddha", "jina", "śāstṛ", "bhadanta"}
CORE_TERMS = {"dharma", "saṃgha", "saṅgha", "nirvāṇa", "karman", "karma", "skandha", "dhyāna", "samādhi", "prajñā", "śīla", "duḥkha", "anitya",
              "anātman", "tṛṣṇā", "āsrava", "sūtra", "vinaya", "abhidharma", "smṛti", "vipaśyanā", "śamatha", "maitrī", "karuṇā", "muditā",
              "upekṣā", "bodhi", "saṃsāra", "vipāka", "kleśa", "nīvaraṇa", "bodhyaṅga", "indriya", "ṛddhipāda", "smṛtyupasthāna", "mārga",
              "phala", "srotāpanna", "sakṛdāgāmin", "anāgāmin", "ārya", "pṛthagjana", "paramārtha", "saṃvṛti", "nāmarūpa", "vijñāna",
              "vedanā", "saṃjñā", "saṃskāra", "āyatana", "pratītyasamutpāda", "nidāna", "avidyā", "upādāna", "bhava", "sparśa", "ṣaḍāyatana",
              "poṣadha", "prātimokṣa", "pāramitā", "pratyekabuddha", "dāna", "puṇya", "pāpa", "akuśala", "kuśala", "cetanā", "citta",
              "caitta", "manaskāra", "prapañca", "dṛṣṭi", "mithyādṛṣṭi", "samyagdṛṣṭi", "vīrya", "kṣānti", "satya", "adhiṣṭhāna",
              "naiṣkramya", "vimukti", "vimokṣa", "śūnyatā", "animitta", "apraṇihita", "satkāya", "vicikitsā", "śīlavrata", "kāmarāga",
              "pratigha", "māna", "auddhatya", "moha", "lobha", "dveṣa", "rāga", "kāma", "vyāpāda", "vihiṃsā", "samyagvāc", "samyakkarmānta",
              "samyagājīva", "samyagvyāyāma", "samyaksmṛti", "samyaksamādhi", "samyaksaṃkalpa", "rūpa", "mantra", "vidyā", "sattva", "ātman",
              "pudgala", "jīva", "lakṣaṇa", "nimitta", "dharmaparyāya", "lokadhātu", "kṣetra", "vyūha", "tathatā", "dharmakāya", "rūpakāya",
              "samyaksaṃbodhi", "samyaksambodhi", "prajñāpāramitā", "bodhicitta", "upāya", "kalpa", "yāna", "mahāyāna", "hīnayāna", "śrāvakayāna", "bodhisattvayāna",
              "jarāmaraṇa", "jāti", "upādātṛ", "pratītyasamutpanna", "svabhāva", "parabhāva", "abhāva", "bhāva", "pratyaya", "hetu", "kārya", "kāraṇa",
              "kartṛ", "kāraka", "tathāgata", "viparyāsa", "lakṣya", "utpāda", "sthiti", "bhaṅga", "nirodha", "uccheda", "śāśvata", "ekatva", "anyatva",
              "gati", "gamana", "gantṛ", "indhana", "agni", "bandhana", "mokṣa", "saṃyoga", "saṃsarga", "anta", "madhya", "saṃtāna", "santāna", "ātmabhāva",
              "ādhipateya", "ārambaṇa", "ālambana", "samanantara", "adhipati", "hetupratyaya", "anekatva", "nānātva", "kārakatva", "upāyāsa",
              "parideva", "śoka", "maraṇa", "daurmanasya"}


_CASE_ORDER = {"nom": 0, "acc": 1, "instr": 2, "dat": 3, "abl": 4, "gen": 5, "loc": 6, "voc": 7}
_NUMBER_ORDER = {"sg": 0, "pl": 1, "dual": 2}


def _parse_order(parse: str, pos: str) -> tuple:
    """The stem's own gender first, then singular before plural before dual, nominative before the other cases."""
    bits = parse.split()
    gender = bits[0] if bits and bits[0] in ("masc", "fem", "nt") else ""
    rest = bits[1:] if gender else bits
    case = next((b for b in rest if b in _CASE_ORDER), "")
    number = next((b for b in rest if b in _NUMBER_ORDER), "")
    own = 0 if (pos not in ("masc", "fem", "nt") or gender == pos) else 1
    return (own, _NUMBER_ORDER.get(number, 3), _CASE_ORDER.get(case, 9), {"masc": 0, "nt": 1, "fem": 2}.get(gender, 3))


def _classify(stem: str, meaning: str, pali: str = "") -> str:
    """'name', 'honorific', 'technical' or '' for a Sanskrit headword."""
    s = stem.lower()
    if s in HONORIFICS:
        return "honorific"
    if s in CORE_TERMS:
        return "technical"
    if meaning and Cologne.is_name_body(meaning):
        return "name"
    return ""
