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
    assert "`dhamma` (teaching)" in fixed4 and "`saṃsāraṃ` (cycle of rebirth)" in fixed4


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
    assert "this `dhamma` (teaching)" in fixed and "`saṃsāra` (cycle of rebirth)" in fixed



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
