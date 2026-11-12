import pytest
from kavi.config import Settings
from kavi.dpd import DPD, analyse_text
from kavi.lint import lint

s = Settings()
pytestmark = pytest.mark.skipif(not s.dpd_db.exists(), reason="dpd.db not available")


@pytest.fixture(scope="module")
def dpd():
    return DPD(s.dpd_db, s.decon_db, s.decon_json)


def test_names_and_honorifics_are_restored(dpd):
    pali = "Ekaṃ samayaṃ bhagavā bārāṇasiyaṃ viharati isipatane migadāye. Tatra kho bhagavā pañcavaggiye bhikkhū āmantesi."
    draft = "At one time the Blessed One was dwelling at Bārāṇasī in the Deer Park at Isipatana. There the Blessed One addressed the group of five monks."
    an = analyse_text(dpd, pali)
    fixed, findings = lint(an, draft, s.glossary_map)
    assert "Blessed One" not in fixed and "Bhagavā" in fixed
    assert "Deer Park" not in fixed and "Migadāya" in fixed and "bhikkhū" in fixed
    kinds = {f.word: f.severity for f in findings}
    assert kinds.get("kho") == "ask"                 # dropped particle: the reviewer must add it
    assert kinds.get("viharati") == "fix" and "dwells" in fixed   # present rendered as past: fixed


def test_glossary_term_form(dpd):
    pali = "Avijjāpaccayā, bhikkhave, saṅkhārā; saṅkhārapaccayā viññāṇaṃ."
    draft = "Caused by ignorance, monks, mental constructions; caused by mental constructions, consciousness."
    an = analyse_text(dpd, pali)
    fixed, findings = lint(an, draft, s.glossary_map)
    assert "`viññāṇaṃ` (consciousness)" in fixed and "`saṅkhārā` (mental constructions)" in fixed
    assert "bhikkhave" in fixed and "monks" not in fixed


def test_second_occurrence_and_particles(dpd):
    pali = "“Acchariyaṃ, bhante, abbhutaṃ, bhante. Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca. Yadi ce vadeyya, kammāsadhammaṃ nāma kurūnaṃ nigamo.”"
    draft = "“It is wonderful, Bhante; it is marvellous, Venerable sir. Seated to one side, the venerable Ānanda said this to the Blessed One. If he should say, a market town of the Kurus named Kammāsadhamma.”"
    an = analyse_text(dpd, pali)
    fixed, findings = lint(an, draft, s.glossary_map)
    assert "Venerable sir" not in fixed and fixed.count("Bhante") == 2
    assert "Blessed One" not in fixed and "Bhagavā" in fixed
    assert "`nāma`" not in fixed                      # 'named' is the ordinary sense, not the technical nāma
    assert not any(f.word == "ce" for f in findings)   # 'if' is there


def test_tense_and_heading(dpd):
    an = analyse_text(dpd, "Ekaṃ samayaṃ bhagavā kurūsu viharati.")
    fixed, findings = lint(an, "At one time the Blessed One was living among the Kurus.", s.glossary_map)
    assert "lives among" in fixed and "the Bhagavā lives" in fixed
    an2 = analyse_text(dpd, "Paṭiccasamuppāda")
    fixed2, _ = lint(an2, "Dependent Origination (Paṭiccasamuppāda)", s.glossary_map)
    assert fixed2 == "`Paṭiccasamuppāda` (Dependent Origination)"
    fixed3, _ = lint(an2, "2.1 Paṭiccasamuppāda", s.glossary_map)
    assert fixed3 == "2.1 `Paṭiccasamuppāda` (dependent origination)"
    an3 = analyse_text(dpd, "Etassa dhammassa ananubodhā saṃsāraṃ nātivattati.")
    fixed4, _ = lint(an3, "Through non-comprehension of this teaching it does not transcend the cycle of rebirth.", s.glossary_map)
    assert "this teaching" in fixed4 and "`saṃsāraṃ` (cycle of rebirth)" in fixed4      # dhamma is left to the translator


def test_italic_pali_duplicates(dpd):
    an = analyse_text(dpd, "Gambhīro cāyaṃ paṭiccasamuppādo. Saṃsāraṃ nātivattati.")
    fixed, _ = lint(an, "How deep this dependent origination (*paṭiccasamuppāda*) is. It does not transcend the cycle of rebirth (*saṃsāra*).", s.glossary_map)
    assert "`paṭiccasamuppādo` (dependent origination)" in fixed and "(*paṭiccasamuppāda*)" not in fixed
    assert "`saṃsāraṃ` (cycle of rebirth)" in fixed and "(*saṃsāra*)" not in fixed


def test_tense_check_skips_ambiguous_verbs(dpd):
    an = analyse_text(dpd, "Jātiyā ca hi asati sabbena sabbaṃ.")
    _, findings = lint(an, "And when there was no birth at all.", s.glossary_map)
    assert not any(f.word == "asati" for f in findings)


def test_bare_stem_gets_gloss(dpd):
    an = analyse_text(dpd, "Etassa dhammassa ananubodhā saṃsāraṃ nātivattati.")
    fixed, _ = lint(an, "Through non-comprehension of this Dhamma it does not transcend the cycle of saṃsāra.", s.glossary_map)
    assert "this Dhamma" in fixed and "`saṃsāra` (cycle of rebirth)" in fixed             # dhamma stays as rendered
    an2 = analyse_text(dpd, "Pañca khandhā.")
    fixed2, _ = lint(an2, "The five khandha.", s.glossary_map)
    assert "`khandha` (collection)" in fixed2



def test_glossary_gloss_replaces_other_renderings(dpd):
    an = analyse_text(dpd, "Nāmarūpapaccayā phasso; nāmarūpaṃ.")
    fixed, _ = lint(an, "With name-and-form as condition, contact; name and form arises.", s.glossary_map)
    assert "name-and-form" not in fixed and "name and form" not in fixed
    assert "`nāmarūpaṃ` (phenomenal objects)" in fixed or "phenomenal objects" in fixed


def test_no_edit_inside_term_span_and_alternatives(dpd):
    alts = {"saṅkhāra": ["mental fabrication"], "nāmarūpa": ["name and form"]}
    an = analyse_text(dpd, "Katamo paṭiccasamuppādo? Saṅkhāranirodhā viññāṇanirodho; nāmarūpanirodhā saḷāyatananirodho. Evametassa samudayo hoti.")
    draft = "What is `paṭiccasamuppādo` (dependent origination)? With the cessation of mental fabrications, consciousness ends; with the cessation of name-and-form, the six sense bases end. Such is the origin of this."
    fixed, _ = lint(an, draft, s.glossary_map, alternatives=alts)
    assert "(dependent origination)" in fixed and "`samudayo`" not in fixed.split("?")[0]
    assert "mental fabrications" not in fixed and "mental constructions" in fixed
    assert "name-and-form" not in fixed and "phenomenal objects" in fixed


def test_glossary_alternative_substring_of_gloss():
    from kavi.dpd import Headword, Analysis
    h = Headword(1, "niṣṭhanirvāṇa", "niṣṭhanirvāṇa", "nt", "", "ultimate extinguishment", "", "", "", "", "", "", "")
    an = [Analysis(surface="niṣṭhanirvāṇaḥ", key="niṣṭhanirvāṇa", headwords=[h])]
    glossary = {"niṣṭhanirvāṇa": "ultimate extinguishment (of suffering)"}
    alts = {"niṣṭhanirvāṇa": ["ultimate extinguishment"]}
    draft = "He has reached the ultimate extinguishment."
    fixed, _ = lint(an, draft, glossary, alternatives=alts)
    assert "ultimate extinguishment (of suffering)" in fixed
    assert "(of suffering) (of suffering)" not in fixed


def test_sanskrit_honorifics_and_technical_terms():
    from kavi.dpd import Headword, Analysis
    from kavi.language import LANGUAGE
    from kavi.interlinear import format_mantra

    orig_code = LANGUAGE["code"]
    try:
        LANGUAGE["code"] = "sa"
        # 1. Vocative honorific: first encounter gets (meaning), subsequent encounter gets untranslated vocative form
        h_voc = Headword(1, "bhagavat", "bhagavat", "masc", "", "Blessed One", "", "", "", "", "", "", "", parses=["voc sg"])
        an_voc = [Analysis(surface="bhagavan", key="bhagavan", headwords=[h_voc])]
        # no parenthetical explanation of an honorific, on first use or after
        fixed_plain, _ = lint(an_voc, "Tell me, O Blessed One.", {})
        assert "Bhagavan" in fixed_plain
        assert "(the Blessed One)" not in fixed_plain
        assert "O " not in fixed_plain

        # Formulaic rule: Thus have I heard -> Thus heard by me
        fixed_thus, _ = lint([], "Thus have I heard: at one time.", {})
        assert fixed_thus.startswith("Thus heard by me:")

        # 2. Sanskrit technical term: first encounter gets `term` (gloss), subsequent encounter gets bare term
        h_term = Headword(2, "pratītyasamutpāda", "pratītyasamutpāda", "masc", "", "dependent origination", "", "", "", "", "", "", "", parses=["nom sg"])
        an_term = [Analysis(surface="pratītyasamutpādaḥ", key="pratītyasamutpāda", headwords=[h_term])]
        sa_glossary = {"pratītyasamutpāda": "dependent origination"}
        term_glossed = set()
        t1, _ = lint(an_term, "He taught dependent origination.", sa_glossary, glossed=term_glossed)
        assert "`pratītyasamutpāda` (dependent origination)" in t1

        t2, _ = lint(an_term, "Seeing dependent origination, one sees the Dhamma.", sa_glossary, glossed=term_glossed)
        assert "pratītyasamutpāda" in t2
        assert "dependent origination" not in t2

        # 3. Mantra formatting
        m_src = "tadyathā: gate gate pāragate pārasaṃgate bodhi svāhā||"
        m_tr = "as follows: gone, gone, gone beyond, completely gone beyond, awakening, hail."
        res = format_mantra(m_src, m_tr)
        assert res.startswith("as follows: gate gate pāragate pārasaṃgate bodhi svāhā (gone, gone, gone beyond")
    finally:
        LANGUAGE["code"] = orig_code



from kavi.dpd import Analysis, Headword
from kavi.language import set_language


def test_sanskrit_honorifics_are_written_only_where_the_source_has_them():
    set_language(type("L", (), {"language": "Sanskrit", "code": "sa", "pronouns": None})())
    try:
        text = "The teacher of grammar said to the elder: the lord of the city heard this verse from a guide."
        fixed, _ = lint([], text, {})
        assert fixed == text
        h = Headword(1, "śāstṛ", "śāstṛ", "masc", "", "teacher", "", "", "", "", "", "", "", parses=["masc nom sg"])
        fixed, _ = lint([Analysis(surface="śāstā", key="śāstā", headwords=[h])], "The teacher spoke.", {})
        assert "Śāstṛ" in fixed
    finally:
        set_language(type("L", (), {"language": "Pāli", "code": "pi", "pronouns": None})())


def test_the_shipped_glossaries_have_one_line_per_term():
    from collections import Counter
    from pathlib import Path
    import kavi
    for f in (Path(kavi.__file__).parent / "glossaries").glob("*.txt"):
        terms = [ln.partition(":")[0].strip() for ln in f.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.strip().startswith("#") and ":" in ln]
        assert not [t for t, n in Counter(terms).items() if n > 1], f.name


def test_every_alternative_gives_way_and_alms_is_no_plural():
    set_language(type("L", (), {"language": "Sanskrit", "code": "sa", "pronouns": None})())
    try:
        h = Headword(1, "piṇḍapāta", "piṇḍapāta", "masc", "", "alms-food", "", "", "", "", "", "", "", parses=["masc dat sg"])
        an = [Analysis(surface="piṇḍapātāya", key="piṇḍapātāya", headwords=[h])]
        fixed, _ = lint(an, "He went into the city for alms.", {"piṇḍapāta": "alms-food"}, alternatives={"piṇḍapāta": ["alms food", "alms"]})
        assert "piṇḍapātas" not in fixed and "alms-foods" not in fixed
    finally:
        set_language(type("L", (), {"language": "Pāli", "code": "pi", "pronouns": None})())
    h = Headword(1, "paccaya", "paccaya", "masc", "", "cause", "", "", "", "", "", "", "", parses=["masc nom sg"])
    an = [Analysis(surface="paccayo", key="paccayo", headwords=[h])]
    fixed, _ = lint(an, "A requisite arises from a condition.", {"paccaya": "cause"}, alternatives={"paccaya": ["condition", "requisite"]}, glossed={"paccaya"})
    assert "condition" not in fixed and "requisite" not in fixed
