import pytest
from kavi.config import Settings
from kavi.dpd import DPD, analyse_text, analysis_table, reference_pairs, special_words

s = Settings()
pytestmark = pytest.mark.skipif(not s.dpd_db.exists(), reason="dpd.db not available")


@pytest.fixture(scope="module")
def dpd():
    return DPD(s.dpd_db, s.decon_db, s.decon_json)


def test_inflected_form(dpd):
    a = dpd.analyse("bhikkhave")
    assert a.found and any(h.stem == "bhikkhu" for h in a.headwords)
    assert "vocative plural" in a.headwords[0].analysis
    b = dpd.analyse("bhikkhū")
    assert b.headwords[0].stem == "bhikkhu"          # the noun the texts use, not the rare aorist homonym


def test_sandhi_via_deconstructor(dpd):
    a = dpd.analyse("Tatthodantāsarā".lower())
    assert a.found and a.best_split is not None and a.best_split.complete


def test_specials(dpd):
    analyses = analyse_text(dpd, "Ekaṃ samayaṃ bhagavā bārāṇasiyaṃ viharati isipatane migadāye. Pañcupādānakkhandhā dukkhā, bhante. Atha kho Koṇḍañño Xyzavo ca.")
    sp = special_words(analyses)
    names = {g for _, g in sp["name"]}
    assert "Bārāṇasī" in names
    assert any("bhagav" in g for _, g in sp["honorific"]) or any("bhante" in w for w, _ in sp["honorific"])
    table = analysis_table(analyses)
    assert table.startswith("| Word |") and "bārāṇasiyaṃ" in table.lower()
    assert reference_pairs(analyses)
    assert "Xyzavo" in {w for w, _ in sp["name"]} and "Ekaṃ" not in {w for w, _ in sp["name"]}


def test_lengthened_final_and_curated_splits(dpd):
    a = dpd.analyse("khāyatī")
    assert a.best_split is not None and a.best_split.parts == ["khāyati"]
    b = dpd.analyse("atthītissa")
    assert b.best_split is not None and b.best_split.parts == ["atthi", "iti", "assa"]


def test_name_homonym_needs_capital(dpd):
    low = dpd.analyse("dhammā")
    assert low.headwords[0].kind != "name" and low.governing({}).stem == "dhamma"
    cap = dpd.analyse("Dhammā", mid_capital=True)
    assert cap.governing({}).kind == "name"
