"""The interlinear mode: tokens, candidate parses from the DPD, symbol rendering, the model answer, and the
document assembly with a fake model."""
import json

import pytest
from kavi.config import Settings
from kavi.dpd import DPD
from kavi.interlinear import (Interlinear, Parse, analyse_tokens, is_pali, load_segments, match_segments,
                              parse_answer, tokenise)
from kavi.models import Reply

s = Settings()
needs_dpd = pytest.mark.skipif(not s.dpd_db.exists(), reason="dpd.db not available")


@pytest.fixture(scope="module")
def dpd():
    return DPD(s.dpd_db, s.decon_db, s.decon_json)


def test_symbols_follow_the_textbook_order():
    assert Parse("noun", "bhagavant", gender="masc", case="nom", number="sg").symbols() == "🚹⨀①(bhagavant)"
    assert Parse("verb", "viharati", number="sg", person="3rd", tense="pr").symbols() == "🟢⨀🤟▶️(viharati)"
    assert Parse("verb", "vadati", number="pl", person="2nd", tense="opt", voice="reflx").symbols() == "🔵⨂🤘⏯(vadati)"
    assert Parse("pron", "ahaṁ", person="1st", case="instr", number="sg").symbols() == "*️⃣👆⚧⨀③(ahaṁ)"
    assert Parse("pron", "ta", person="3rd", gender="masc", case="gen", number="sg").symbols() == "*️⃣🤟🚹⨀⑥(ta)"
    assert Parse("noun", "nisinna", gender="masc", case="nom", number="sg", affix="na").symbols() == "🚹⨀①🔽(na)(nisinna)"
    assert Parse("noun", "bodhirukkhamūla", gender="nt", case="loc", number="sg", members=["bodhirukkha", "mūla"]).symbols() == "🚻⨀⑦🆎(bodhirukkha+mūla)"
    assert Parse("affix", "vuṭṭhahati", affix="tvā").symbols() == "🔽(tvā)(vuṭṭhahati)"
    assert Parse("ind", "evaṁ").symbols() == "⏏️(evaṁ)"
    assert Parse("noun", "dvi", gender="x", case="nom", number="pl").symbols() == "⚧⨂①(dvi)"


def test_tokenise_drops_quotes_and_restores_the_niggahita_before_ti():
    toks = tokenise("“Yato pajānāti sahetudhamman”ti.")
    assert [t[0] for t in toks] == ["Yato", "pajānāti", "sahetudhamman", "ti"]
    assert toks[2][1] == "sahetudhammaṃ"
    toks = tokenise("Evaṁ me sutaṁ— ekaṁ samayaṁ, bhagavā viharati:")
    assert [t[0] for t in toks] == ["Evaṁ", "me", "sutaṁ", "ekaṁ", "samayaṁ", ",", "bhagavā", "viharati"]
    assert toks[5][2] is True


def test_parse_answer_tolerates_prose_around_the_json():
    tokens = [object(), object(), object()]
    choice, gloss, tr = parse_answer('Here: {"words": [{"n": 1, "parse": 2, "gloss": "thus"}, {"n": 3, "parse": "x", "gloss": "heard"}], "translation": "Thus heard."} ok', tokens)
    assert choice == {1: 2} and gloss == {1: "thus", 3: "heard"} and tr == "Thus heard."
    choice, gloss, tr = parse_answer("nothing useful", tokens)
    assert choice == {} and gloss == {} and tr == ""


def test_segments_match_a_paragraph(tmp_path):
    f = tmp_path / "ud.json"
    f.write_text(json.dumps({"root_text": {"ud1.1:0.1": "Udāna 1.1 ", "ud1.1:1.1": "Evaṁ me sutaṁ—", "ud1.1:1.2": "ekaṁ samayaṁ bhagavā viharati. ", "ud1.1:2.1": "Atha kho. "}}), encoding="utf-8")
    segs = load_segments(f)
    assert segs[0] == ("1.1", "Evaṁ me sutaṁ—")
    m = match_segments("Evaṁ me sutaṁ— ekaṁ samayaṁ bhagavā viharati.", segs, 0)
    assert m is not None and [n for n, _ in m[0]] == ["1.1", "1.2"] and m[1] == 2
    assert match_segments("Something else entirely.", segs, 0) is None


@needs_dpd
def test_candidates_from_the_dictionary(dpd):
    toks = analyse_tokens(dpd, "Evaṁ me sutaṁ— ekaṁ samayaṁ bhagavā uruvelāyaṁ viharati.")
    by = {t.surface: t for t in toks}
    me = by["me"].candidates
    assert {(p.kind, p.person, p.case) for p in me} >= {("pron", "1st", "acc"), ("pron", "1st", "instr"), ("pron", "1st", "dat")}
    assert by["bhagavā"].candidates[0].symbols() == "🚹⨀①(bhagavant)"
    assert by["uruvelāyaṁ"].candidates[0].symbols() == "🚺⨀⑦(uruvelā)"
    assert by["viharati"].candidates[0].symbols() == "🟢⨀🤟▶️(viharati)"
    assert by["Evaṁ"].candidates[0].symbols() == "⏏️(evaṁ)"


@needs_dpd
def test_sandhi_and_compounds_are_isolated(dpd):
    toks = analyse_tokens(dpd, "imassuppādā idaṁ uppajjati bodhirukkhamūle vuṭṭhahitvā hotī”ti")
    surfaces = [t.surface for t in toks]
    assert surfaces[:2] == ["imassa", "uppādā"]
    by = {t.surface: t for t in toks}
    assert by["bodhirukkhamūle"].candidates[0].members == ["bodhirukkha", "mūla"]
    assert by["vuṭṭhahitvā"].candidates[0].symbols() == "🔽(tvā)(vuṭṭhahati)"
    assert by["hotī"].candidates and by["hotī"].candidates[0].lemma == "hoti"
    assert by["ti"].candidates[0].symbols() == "⏏️(iti)"


@needs_dpd
def test_is_pali(dpd):
    assert is_pali(dpd, "Evaṁ me sutaṁ— ekaṁ samayaṁ bhagavā uruvelāyaṁ viharati.")
    assert not is_pali(dpd, 'Part of "A Beginner (Non-Linguist) Guide to Learning Pali"')


class FakeModel:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def chat(self, messages, **kw):
        self.calls.append(messages)
        first = messages[-1]["content"].split("\n")[0]          # the "Sentence: …" line, not the context lines
        for key, answer in self.answers:
            if key in first:
                return Reply(answer, "stop", 10, 0.1)
        return Reply("{}", "stop", 1, 0.1)


class FakePool:
    def __init__(self, model):
        self.model = model

    def get(self, role):
        return self.model

    def release(self, role):
        pass


@needs_dpd
def test_document_with_a_fake_model(dpd, tmp_path):
    text = ('---\ntitle: x\n---\n\n:::tip[Info]\nPart of "A Beginner (Non-Linguist) Guide to Learning Pali"\n:::\n\n## Paṭhamabodhisutta\n\n'
            '>Evaṁ me sutaṁ— ekaṁ samayaṁ bhagavā uruvelāyaṁ viharati.\n\n>“Yadā have pātubhavanti dhammā,\nĀtāpino jhāyato brāhmaṇassa.\n')
    model = FakeModel([
        ("Sentence: Evaṁ me sutaṁ", '{"words": [{"n": 1, "parse": 1, "gloss": "thus"}, {"n": 2, "parse": 2, "gloss": "by me"}, {"n": 3, "parse": 1, "gloss": "heard"}], "translation": "Thus it was heard by me—"}'),
        ("Sentence: ekaṁ samayaṁ", '{"words": [{"n": 1, "parse": 1, "gloss": "one"}, {"n": 2, "parse": 1, "gloss": "time"}, {"n": 3, "parse": 1, "gloss": "the Blessed One"}, {"n": 4, "parse": 1, "gloss": "at Uruvelā"}, {"n": 5, "parse": 1, "gloss": "dwells"}], "translation": "At one time the Blessed One dwells at Uruvelā."}'),
        ("Yadā have pātubhavanti", '{"words": [{"n": 1, "parse": 1, "gloss": "when"}, {"n": 2, "parse": 1, "gloss": "indeed"}, {"n": 3, "parse": 1, "gloss": "appear"}, {"n": 4, "parse": 1, "gloss": "phenomena"}], "translation": "When indeed phenomena appear,"}'),
        ("Ātāpino jhāyato", '{"words": [{"n": 1, "parse": 1, "gloss": "ardent"}, {"n": 2, "parse": 1, "gloss": "meditating"}, {"n": 3, "parse": 1, "gloss": "to the brahmin"}], "translation": "to the ardent, meditating brahmin."}'),
    ])
    st = Settings()
    st.cache_dir = tmp_path
    inter = Interlinear(st, dpd, FakePool(model), progress=lambda m: None, use_cache=False)
    segments = [("0.2", "Paṭhamabodhisutta"), ("1.1", "Evaṁ me sutaṁ—"), ("1.2", "ekaṁ samayaṁ bhagavā uruvelāyaṁ viharati. ")]
    res = inter.translate_markdown(text, segments)
    out = res.markdown
    assert out.startswith("---\ntitle: x\n---")
    assert 'Part of "A Beginner' in out and "## Paṭhamabodhisutta" in out
    assert "1.1 Evaṁ me sutaṁ—  \n⏏️(evaṁ) *️⃣👆⚧⨀③(ahaṁ) " in out                      # parse 2 of "me": instrumental
    assert "thus | by me | heard  \n" in out
    assert "the Bhagavā" in out and "Blessed One" not in out                              # the checker's convention on line 4
    assert "the Bhagavā | at Uruvelā | dwells" in out                                      # the honorific on line 3 too
    assert "2.1 “Yadā have pātubhavanti dhammā,  " in out and "2.2 Ātāpino" in out      # the quotation mark stays
    assert out.rstrip().endswith("When indeed phenomena appear,  \nto the ardent, meditating brahmin.")
    assert ">" not in out.split("## Paṭhamabodhisutta")[1]                                # the blockquotes are replaced
    assert len(model.calls) == 4
