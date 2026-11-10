"""The Sanskrit layer: the Cologne parser, the hybrid readings and the key variants need no data; the lexicon tests
run only when `kavi setup --sanskrit` has been done."""

from pathlib import Path

import pytest

from kavi.bhs import readings
from kavi.cologne import clean_body, iter_entries, slp1_to_iast

DATA = Path(__file__).resolve().parents[1] / "data"
HAVE_DATA = (DATA / "vidyut" / "kosha").exists() and (DATA / "sanskrit.sqlite").exists()


def test_slp1_to_iast():
    assert slp1_to_iast("boDisattva") == "bodhisattva"
    assert slp1_to_iast("SUnyatA") == "śūnyatā"
    assert slp1_to_iast("saMskAra") == "saṃskāra"
    assert slp1_to_iast("kfzRa") == "kṛṣṇa"


def test_clean_body_mw_and_bhs():
    text, lex, pali = clean_body("<s>vi-√ hf</s> ¦ <ab>P.</ab> <s>-harati</s>, to put asunder, <ls>RV.</ls>;<div n=\"to\"/>to disperse", "mw")
    assert text.startswith("vi-√ hṛ P. -harati, to put asunder, RV.; to disperse"), text
    text, lex, pali = clean_body("{@bodhisattva@}¦ (= <lang>Pali</lang> ˚satta), {%person destined for enlightenment%}, <ls>Mvy</ls> 〔625〕", "bhs")
    assert "person destined for enlightenment" in text and pali == "satta"
    text, lex, pali = clean_body("{#vihf#}¦ {c1c} <ab>P.</ab> {@1@} To take away", "ap90")
    assert text.startswith("vihṛ P. 1 To take away")


def test_iter_entries(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("<L>1<pc>001,1<k1>a<k2>a-, an-\n{@a-, an-@}¦, negative prefix\n<LEND>\n<L>2<pc>001,1<k1>aMSa<k2>aMSa<h>1\nbody two\n<LEND>\n", encoding="utf-8")
    entries = list(iter_entries(f))
    assert [e["k1"] for e in entries] == ["a", "aMSa"] and entries[1]["h"] == "1" and entries[1]["body"] == "body two"


def test_bhs_readings():
    assert ("bhavet", "§ 29.28 optative in -eya") in readings("bhaveya")
    assert any(r[0] == "loke" for r in readings("lokasmiṃ"))
    assert any(r[0] == "bodhisattvaḥ" for r in readings("bodhisatvo"))
    assert any(r[0] == "ekānte" for r in readings("ekāṃte"))
    assert any(r[0] == "sahasra" for r in readings("sahastra"))
    assert any(r[0] == "āyuṣmantam" for r in readings("āyusmantam"))


def test_panini_rules():
    from kavi.panini import (
        compound_junction_variants,
        external_sandhi_cands,
        is_agent_tr,
        undo_initial_vrddhi,
        undo_natva,
        undo_satva,
    )
    assert is_agent_tr("kartṛ") and is_agent_tr("gantṛ") and is_agent_tr("bhoktṛ")
    assert not is_agent_tr("pitṛ") and not is_agent_tr("mātṛ") and not is_agent_tr("svasṛ")
    assert "namati" in undo_natva("pra", "ṇamati")
    assert "sthitam" in undo_satva("prati", "ṣṭhitam")
    assert "durmanas" in undo_initial_vrddhi("daurmanas")
    assert "loka" in undo_initial_vrddhi("lauka")
    assert ("niḥ", "roga") in compound_junction_variants("nī", "roga")
    assert ("mahā", "ṛṣi") in compound_junction_variants("mahar", "ṣi")
    assert ("eka", "bhūta") in compound_junction_variants("ekī", "bhūta")
    assert ("punar", "ramate") in external_sandhi_cands("punāramate", 3)
    assert ("antaḥ", "śauṣiryam") in external_sandhi_cands("antaḥśauṣiryam", 4)


@pytest.mark.skipif(not HAVE_DATA, reason="Sanskrit data not installed (kavi setup --sanskrit)")
def test_lexicon_words():
    from kavi.sanskrit import SanskritLexicon, key_variants
    assert "Darmas" in key_variants("dharmaḥ") and "budDAnAm" in key_variants("buddhānāṃ") and "tAn" in key_variants("tāṃś")
    lx = SanskritLexicon(DATA)
    a = lx.analyse("viharati")
    assert a.headwords[0].lemma == "viharati" and a.headwords[0].pos == "pr" and "pr 3rd sg" in a.headwords[0].parses
    a = lx.analyse("bodhisattvaḥ")
    assert a.headwords[0].lemma == "bodhisattva" and "masc nom sg" in a.headwords[0].parses and a.headwords[0].kind == "honorific"
    a = lx.analyse("anutpannā")
    assert a.headwords[0].pos == "pp" and a.headwords[0].construction.startswith("na + utpanna")
    a = lx.analyse("mayā")
    assert a.headwords[0].lemma == "aham" and a.headwords[0].pos == "pron"
    a = lx.analyse("ekasmin")
    assert a.headwords[0].lemma == "eka" and "loc sg" in a.headwords[0].parses[0]
    a = lx.analyse("bodhisatvo")
    assert a.headwords[0].lemma == "bodhisattva" and "2.84" in a.note
    a = lx.analyse("prajñāpāramitācaryāṃ")
    assert a.headwords[0].construction.startswith("prajñā + pāramitā + cary")
    a = lx.analyse("kaścit")
    assert a.headwords[0].lemma == "kaścit" and a.headwords[0].pos == "pron" and a.headwords[0].construction == "kim + cit"
    a = lx.analyse("nāvidyā")                                        # two words: the particle and the term, which stays whole
    assert not a.headwords and a.splits[0].parts == ["na", "avidyā"]
    a = lx.analyse("vedanā-saṃjñā-saṃskāra-vijñānaṃ")                # a hyphenated compound is one word with its members
    assert a.headwords[0].construction == "vedanā + saṃjñā + saṃskāra + vijñāna"
    a = lx.analyse("tadyathā")
    assert a.headwords[0].pos == "ind" and a.headwords[0].construction == "tad + yathā"
    a = lx.analyse("amithyātvāt")
    assert a.headwords[0].construction == "na + mithyā + tva" and a.headwords[0].parses == ["nt abl sg"]
    a = lx.analyse("āryāvalokiteśvaro")                             # an epithet and a name: one name
    assert a.headwords[0].kind == "name" and not a.headwords[0].construction
    a = lx.analyse("rūpam")                                          # the dictionary's gender first
    assert a.headwords[0].pos == "nt" and a.headwords[0].parses[0] == "nt nom sg"
    a = lx.analyse("tathāgatāyārhate")                              # two inflected words, not a compound of scraps
    assert not a.headwords and a.splits[0].parts == ["tathāgatāya", "arhate"]
    a = lx.analyse("bodhi")                                          # the hybrid vocative in -i
    assert a.headwords[0].lemma == "bodhi" and "fem voc sg" in a.headwords[0].parses
    # the Diamond Sūtra's lessons (2026-11-02)
    a = lx.analyse("samanupaśyati")                                  # a prefixed verb the kosha lacks: sam + anu + paśyati
    assert a.headwords[0].lemma == "samanupaśyati" and a.headwords[0].pos == "pr" and "pr 3rd sg" in a.headwords[0].parses
    a = lx.analyse("paryavāpnuyāt")                                  # two prefixes: pary + av + āpnoti
    assert a.headwords[0].lemma == "paryavāpnoti" and a.headwords[0].pos == "opt"
    a = lx.analyse("arhate")                                         # an honorific is a noun, not the participle of arhati
    assert a.headwords[0].lemma == "arhat" and a.headwords[0].pos in ("masc", "adj") and a.headwords[0].kind == "honorific"
    a = lx.analyse("subhūte")                                        # the disciple, masculine, before the adjective subhūta
    assert a.headwords[0].lemma == "subhūti" and a.headwords[0].kind == "name" and a.headwords[0].parses == ["masc voc sg"]
    a = lx.analyse("anāthapiṇḍadasya")                               # a name stays whole, not na + nātha + piṇḍada
    assert a.headwords[0].kind == "name" and not a.headwords[0].construction
    a = lx.analyse("bhagavan")
    assert a.headwords[0].lemma == "bhagavat" and a.headwords[0].pos == "masc" and a.headwords[0].parses == ["masc voc sg"]
    a = lx.analyse("mahān")                                          # a strong form of mahat the kosha lacks
    assert a.headwords[0].lemma == "mahat" and "masc nom sg" in a.headwords[0].parses
    a = lx.analyse("sa")                                             # saḥ before a consonant: the nominative, not only the vocative
    assert a.headwords[0].lemma == "tad" and a.headwords[0].parses[0] == "masc nom sg"
    a = lx.analyse("āha")                                            # the perfect used as a present, as the author writes it
    assert a.headwords[0].lemma == "āha" and a.headwords[0].pos == "perf"
    a = lx.analyse("yāvaṃtaḥ")                                       # yāvat the adjective; the particle only when spelt so
    assert a.headwords[0].lemma == "yāvat" and a.headwords[0].pos == "adj"
    a = lx.analyse("sārdham")
    assert a.headwords[0].pos == "ind"
    a = lx.analyse("satvasaṃjñā")                                    # the member sattva (not satvan), the noun saṃjñā
    assert a.headwords[0].construction == "sattva + saṃjñā"
    a = lx.analyse("adhātuḥ")                                        # na + dhātu before two chance words
    assert a.headwords[0].construction == "na + dhātu"
    a = lx.analyse("upasaṃkkramya")
    assert a.headwords[0].pos == "abs" and a.headwords[0].lemma == "upasaṃkrāmati"
    # Pāṇinian rules & DSBC compound/sandhi tests
    a = lx.analyse("tadeva")
    assert a.splits[0].parts == ["tad", "eva"]
    a = lx.analyse("parakṛtam")
    assert a.headwords[0].construction == "para + kṛta + ta" and a.headwords[0].pos == "pp"
    a = lx.analyse("kiṃcit")
    assert a.headwords[0].lemma == "kaścit" and a.headwords[0].pos == "pron" and a.headwords[0].construction == "kim + cit"
    for agent_form, stem in [("kartā", "kartṛ"), ("gantā", "gantṛ"), ("bhoktā", "bhoktṛ")]:
        a = lx.analyse(agent_form)
        assert a.headwords[0].lemma == stem and a.headwords[0].pos == "masc" and "masc nom sg" in a.headwords[0].parses
    a = lx.analyse("utpādotpādamutpādo")
    assert a.splits[0].parts == ["utpādotpādam", "utpādo"]
    a = lx.analyse("abdhātuḥ")
    assert a.headwords[0].construction == "ap + dhātu"
    a = lx.analyse("kāyasyāntaḥśauṣiryamabhinirvartayati")
    assert a.splits[0].parts == ["kāyasya", "antaḥ", "śauṣiryam", "abhinirvartayati"]
    a = lx.analyse("bhagavānāyusmantamānandamāmantrayate")
    assert a.splits[0].parts == ["bhagavān", "āyusmantam", "ānandam", "āmantrayate"]
    a = lx.analyse("pṛthivyaptejovāyvākāśaṛtudhātusamavāyād")
    assert a.headwords[0].construction == "pṛthivī + ap + tejas + vāyu + ākāśa + ṛtu + dhātu + samavāya"
