"""The pipeline without models: a fake pool returns canned drafts and reviews, so the segment → checker →
review → render loop can be tested offline."""
from pathlib import Path

import pytest
from kavi.config import Settings
from kavi.dpd import DPD
from kavi.models import Reply
from kavi.pipeline import Translator

SA_DATA = Path(__file__).resolve().parents[1] / "data"
HAVE_SA = (SA_DATA / "vidyut" / "kosha").exists() and (SA_DATA / "sanskrit.sqlite").exists()

s = Settings()
pytestmark = pytest.mark.skipif(not s.dpd_db.exists(), reason="dpd.db not available")


class FakeModel:
    def __init__(self, path, answers):
        self.path, self.answers, self.calls = path, answers, []

    def chat(self, messages, **kw):
        self.calls.append(messages)
        text = messages[-1]["content"]
        for key, answer in self.answers:
            if key in text:
                return Reply(answer, "stop", 10, 0.1)
        return Reply("ISSUES:\n- none\n\nREVISED:\n" + "\n".join(f"[{i + 1}] x" for i in range(5)) + "\nEND", "stop", 10, 0.1)


class FakePool:
    def __init__(self, translate, review):
        self.models = {"translate": translate, "review": review}

    def get(self, role):
        return self.models[role]

    def release(self, role):
        pass


@pytest.fixture(scope="module")
def dpd():
    return DPD(s.dpd_db, s.decon_db, s.decon_json)


def test_offline_loop(dpd, tmp_path):
    text = "# Paṭiccasamuppāda\n\n95. Ekaṃ samayaṃ bhagavā kurūsu viharati. Atha kho āyasmā ānando bhagavantaṃ etadavoca.\n\n> Namo tassa.\n"
    translate = FakeModel("mitra-qwen35-translate-mlx-bf16", [
        ("Ekaṃ samayaṃ", "At one time the Blessed One was dwelling among the Kurus. Then the Venerable Ānanda said this to the Blessed One."),
        ("Namo tassa", "Homage to him."),
    ])
    review = FakeModel("mitra-qwen35-it-mlx-bf16", [
        ("Segments to check", "ISSUES:\n- Segment [1]: 'kho' not rendered\n\nREVISED:\n[1] At one time the Bhagavā dwells among the Kurus. Then indeed the Venerable Ānanda said this to the Bhagavā.\n[2] Homage to him.\nEND"),
    ])
    st = Settings()
    st.max_rounds = 3
    st.cache_dir = tmp_path
    tr = Translator(st, dpd, FakePool(translate, review), progress=lambda m: None, use_cache=False)
    result = tr.translate_markdown(text)
    out = result.markdown
    assert out.splitlines()[0] == "# `Paṭiccasamuppāda` (dependent origination)"      # title kept, term form added by the checker
    assert "95. " in out and "Blessed One" not in out and "Bhagavā" in out
    assert "> Homage to him." in out                                                 # blockquote prefix preserved
    unit = result.units[1]
    assert unit.lint and any(f.word == "bhagavā" and f.severity == "fix" for f in unit.lint)
    assert unit.rounds and unit.rounds[0].issues                                     # the reviewer's issue was recorded
    assert len(review.calls) >= 1
    assert "Then indeed" in out                                                      # the revision was applied


def test_agentic_loop_with_instruction_model(dpd, tmp_path):
    text = "95. Ekaṃ samayaṃ bhagavā kurūsu viharati. Atha kho āyasmā ānando bhagavantaṃ etadavoca.\n"
    translate = FakeModel("Qwen3.8-27B-bf16", [
        ("Translate this", "At one time the Bhagavā was dwelling among the Kurus. Then Ānanda said this to the Bhagavā."),
        ("Revise the translation", "At one time the Bhagavā was dwelling among the Kurus. Then indeed the āyasmā Ānanda said this to the Bhagavā."),
    ])
    review = FakeModel("Qwen3.8-27B-bf16", [
        ("Segments to check", "ISSUES:\n- Segment [1]: 'kho' ('indeed') and 'āyasmā' were omitted\n\nREVISED:\n[1] At one time the Bhagavā was dwelling among the Kurus. Then indeed the āyasmā Ānanda said this to the Bhagavā.\nEND"),
    ])
    st = Settings()
    st.max_rounds = 2
    st.cache_dir = tmp_path
    tr = Translator(st, dpd, FakePool(translate, review), progress=lambda m: None, use_cache=False)
    result = tr.translate_markdown(text)
    out = result.markdown
    assert "Then indeed" in out
    assert "āyasmā" in out
    # Verify that the translator model was invoked for revision via the harness
    assert any("Revise the translation" in c[-1]["content"] for c in translate.calls)


def test_contextual_macro_pass_and_interlinear_refinement(dpd, tmp_path):
    text = "Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati. Tatra kho bhagavā bhikkhū āmantesi.\n"
    translate = FakeModel("Qwen3.8-27B-bf16", [
        ("Translate the following", "[1] At one time the Bhagavā was dwelling at Sāvatthī.\n[2] There indeed the Bhagavā addressed the monks."),
        ("Sentence: Ekaṃ samayaṃ", '{"words": [{"n": 1, "parse": 1, "gloss": "one"}, {"n": 2, "parse": 1, "gloss": "time"}], "translation": "At one time the Bhagavā was dwelling at Sāvatthī."}'),
        ("Sentence: Tatra kho", '{"words": [{"n": 1, "parse": 1, "gloss": "there"}, {"n": 2, "parse": 1, "gloss": "indeed"}], "translation": "There indeed the Bhagavā addressed the monks."}'),
    ])
    review = FakeModel("Qwen3.8-27B-bf16", [])
    st = Settings()
    st.max_rounds = 0
    st.cache_dir = tmp_path
    tr = Translator(st, dpd, FakePool(translate, review), progress=lambda m: None, use_cache=False)
    result = tr.translate_markdown(text)
    assert len(result.units) == 2
    # Verify initial contextual draft was captured across discourse pass
    assert result.units[0].initial_draft == "At one time the Bhagavā was dwelling at Sāvatthī."
    assert result.units[1].initial_draft == "There indeed the Bhagavā addressed the monks."
    # Verify that prompt_for passed initial draft to the unit-level refinement call
    unit_prompts = [c[-1]["content"] for c in translate.calls if "Sentence: " in c[-1]["content"]]
    assert any("Initial draft translation from discourse context:" in p for p in unit_prompts)


def test_the_default_model_is_the_ollama_one(monkeypatch):
    from kavi.config import DEFAULT_MODEL, default_model
    from kavi.ollama import is_ollama
    monkeypatch.delenv("KAVI_MODEL", raising=False)
    assert default_model() == DEFAULT_MODEL == "qwen3.8:27b-mlx" and is_ollama(default_model())
    monkeypatch.setenv("KAVI_MODEL", "mlx-community/Qwen3.8-27B-bf16")
    assert default_model() == "mlx-community/Qwen3.8-27B-bf16" and not is_ollama(default_model())


def _fake_run(dpd, tmp_path, text, answers, rounds=0, review_answers=()):
    translate = FakeModel("Qwen3.8-27B-bf16", answers)
    review = FakeModel("Qwen3.8-27B-bf16", list(review_answers))
    st = Settings()
    st.max_rounds = rounds
    st.cache_dir = tmp_path
    tr = Translator(st, dpd, FakePool(translate, review), progress=lambda m: None, use_cache=False)
    return tr.translate_markdown(text), translate, review


def _discourse_prompt(model):
    """The Stage 1 prompt a fake model was sent."""
    return next(c[-1]["content"] for c in model.calls if "Translate the following" in c[-1]["content"])


def _unit(lexicon, line, kind="para"):
    from kavi.interlinear import analyse_tokens
    from kavi.pipeline import Unit
    from kavi.segment import Block
    return Unit(block=Block(kind, [], text="x"), source=line, masked=line, tokens=analyse_tokens(lexicon, line))


needs_sanskrit = pytest.mark.skipif(not HAVE_SA, reason="Sanskrit data not installed (kavi setup --sanskrit)")


@pytest.fixture(scope="module")
def sanskrit_lexicon():
    from kavi.sanskrit import SanskritLexicon
    return SanskritLexicon(SA_DATA)


@pytest.fixture
def sa(sanskrit_lexicon):
    """The Sanskrit lexicon, in force as the language for one test."""
    from kavi.language import set_language
    set_language(sanskrit_lexicon)
    yield sanskrit_lexicon
    set_language(None)


def test_a_context_dependent_term_is_not_wrapped(dpd, tmp_path):
    # `dhamma:` has an empty gloss in the glossary: the translator's rendering stands, with no `dhamma` () span
    text = "Yadā have pātubhavanti dhammā ātāpino jhāyato brāhmaṇassa.\n\nAthassa kaṅkhā vapayanti sabbā.\n"
    res, _, _ = _fake_run(dpd, tmp_path, text, [
        ("Translate the following", "[1] When indeed phenomena appear to the ardent brahmin.\n[2] Then all his doubts vanish."),
        ("Sentence: Yadā have", '{"words": [{"n": 1, "parse": 1, "gloss": "when"}], "translation": "When indeed phenomena appear to the ardent brahmin."}'),
        ("Sentence: Athassa", '{"words": [{"n": 1, "parse": 1, "gloss": "then"}], "translation": "Then all his doubts vanish."}'),
    ])
    assert "()" not in res.en_markdown and res.en_markdown.startswith("When indeed phenomena appear")


def test_a_table_is_rendered(dpd, tmp_path):
    text = "| Pāḷi | x |\n| --- | --- |\n| Namo tassa | y |\n"
    res, _, _ = _fake_run(dpd, tmp_path, text, [])
    assert res.en_markdown.count("|") >= 6                       # no IndexError; the table keeps its shape


def test_a_gloss_is_not_rewritten_by_a_substring_of_the_key(dpd, tmp_path):
    # bhava's alternatives (becoming, being) are for the word bhava, not for the verb bhavati
    text = "Saṅkhārā bhavanti.\n"
    res, _, _ = _fake_run(dpd, tmp_path, text, [
        ("Sentence: Saṅkhārā", '{"words": [{"n": 1, "parse": 1, "gloss": "constructions"}, {"n": 2, "parse": 1, "gloss": "come into being"}], "translation": "Mental constructions come into being."}'),
    ])
    assert res.units[0].tokens[-1].gloss == "come into being"


def test_an_unparsed_answer_is_not_cached(dpd, tmp_path):
    st = Settings()
    st.max_rounds = 0
    st.cache_dir = tmp_path
    bad = FakeModel("Qwen3.8-27B-bf16", [("Sentence: Namo", "garbage with no json")])
    tr = Translator(st, dpd, FakePool(bad, bad), progress=lambda m: None)
    tr.translate_markdown("Namo tassa bhagavato.\n")
    assert tr.cache == {}


def test_other_languages_and_inline_markup_are_left_alone(dpd, tmp_path):
    text = (':::tip[Info]\nPart of "A Beginner (Non-Linguist) Guide to Learning Pali"\n:::\n\n'
            'This page is part of the guide; see [the source](https://example.org/a_b) for the details.\n\n'
            'Akkharāpi akārādayo ekacattālīsaṃ suttantopakārā.\n\n'
            'Evaṃ me sutaṃ[^1] <span id="x">ekaṃ</span> samayaṃ.\n')
    res, translate, _ = _fake_run(dpd, tmp_path, text, [
        ("Translate the following", "[1] The letters too, beginning with a, are forty-one.\n[2] Thus heard by me%%2%% at %%0%%one%%1%% time."),
        ("Sentence: Akkharāpi", '{"words": [{"n": 1, "parse": 1, "gloss": "letters"}], "translation": "The letters too, beginning with a, are forty-one."}'),
        ("Sentence: Evaṃ me sutaṃ", '{"words": [{"n": 1, "parse": 1, "gloss": "thus"}], "translation": "Thus heard by me at one time."}'),
    ])
    en = res.en_markdown
    assert [u.source[:9] for u in res.units] == ["Akkharāpi", "Evaṃ me s"]                 # the English blocks are no units
    assert "see [the source](https://example.org/a_b) for the details." in en and 'Part of "A Beginner' in en
    assert "forty-one" in en                                                                # a grammar's line is still Pāli
    assert "[^1]" in en and '<span id="x">' in en and "</span>" in en and "%%" not in en    # lost markers are put back
    assert not any(t.surface in ("span", "id", "x") for u in res.units for t in u.tokens)
    sent = [c[-1]["content"] for c in translate.calls if "Sentence: Evaṃ" in c[-1]["content"]][0]
    assert "Sentence: Evaṃ me sutaṃ%%2%% %%0%%ekaṃ%%1%% samayaṃ." in sent and "placeholder" in sent


def test_the_discourse_prompt_takes_its_terms_from_the_glossary(dpd, tmp_path):
    text = "Avijjāpaccayā saṅkhārā. Dukkhaṃ ariyasaccaṃ.\n"
    _, translate, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] x\n[2] y")])
    prompt = _discourse_prompt(translate)
    g = Settings().glossary_map
    assert f"dukkha -> {g['dukkha']}" in prompt and "saṅkhāra -> mental construction" in prompt
    assert "Heart" not in prompt and "sarvajña" not in prompt        # no other text's words, no other language's terms


def test_the_gate_judges_the_output_not_a_list_of_phrases():
    from kavi.pipeline import is_strictly_better
    ok, _ = is_strictly_better("He went to the three realms of existence.", "He went to three realms.", "He went to the three realms.", [], {})
    assert ok
    ok, why = is_strictly_better("He [masculine nominative singular] went.", "He went.", "He went.", [], {})
    assert not ok and "grammatical" in why


def test_the_grounded_sentence_stands_unless_something_is_wrong_with_it(dpd, tmp_path):
    # Stage 2 differs widely from the draft and calls the Bhagavā "the Blessed One": the checker mends that, and the
    # grounded sentence (the one the word glosses belong to) is kept; a sentence with grammatical tags is not
    text = "Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati.\n\nTatra kho bhagavā bhikkhū āmantesi.\n"
    res, _, _ = _fake_run(dpd, tmp_path, text, [
        ("Translate the following", "[1] Once the Bhagavā stayed near Sāvatthī.\n[2] There the Bhagavā spoke to the bhikkhū."),
        ("Sentence: Ekaṃ samayaṃ", '{"words": [{"n": 1, "parse": 1, "gloss": "one"}], "translation": "At one time the Blessed One dwells in Sāvatthī."}'),
        ("Sentence: Tatra kho", '{"words": [{"n": 1, "parse": 1, "gloss": "there"}], "translation": "There [indeclinable] indeed the Bhagavā [masculine nominative singular] addressed the bhikkhū."}'),
    ])
    assert res.units[0].final == "At one time the Bhagavā dwells in Sāvatthī." and not res.units[0].rejected
    assert res.units[1].final == "There the Bhagavā spoke to the bhikkhū." and "grammatical" in res.units[1].rejected[0]


def test_a_verse_line_is_read_with_its_verse_and_a_meaning_is_said_once(dpd, tmp_path):
    text = "Yadā have pātubhavanti dhammā,\nĀtāpino jhāyato brāhmaṇassa.\n"
    _, translate, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] x\n[2] y")])
    prompt = next(c[-1]["content"] for c in translate.calls if c[-1]["content"].startswith("Sentence: Ātāpino"))
    assert "one line of this verse" in prompt and "Yadā have pātubhavanti dhammā," in prompt
    assert " — 〃" in prompt


@needs_sanskrit
def test_the_discourse_prompt_lists_names_and_words_of_address(sa):
    # what Stage 1 is told to keep bare, and which forms can be words of address (the model seldom finds them)
    lines = ["sarvapāramitābhis tvaṃ nirmalābhir anindite", "sakṛd apy āśaye śuddhe yas tvāṃ vidhivad īkṣate",
             "buddhaiḥ pratyekabuddhaiś ca śrāvakaiś ca niṣevitā", "kṛpayā lokanāthais tvam ucyase ca na cocyase"]
    units = [_unit(sa, ln) for ln in lines]
    kept = Translator._kept_words(units)
    assert {"Buddha", "pratyekabuddha", "śrāvaka", "lokanātha"} <= set(kept.values())
    address = Translator._address_words(units, kept)
    assert "anindite" in address and "śuddhe" not in address          # a vocative; a locative beside its noun
    title = [_unit(sa, lines[2], "heading")]
    assert Translator._kept_words(title) == {} and Translator._address_words(title, {}) == []   # a title names; it addresses no one


def test_a_word_is_kept_bare_or_offered_as_an_address_never_both(dpd):
    from kavi.language import set_language
    set_language(dpd)
    u = _unit(dpd, "Acchariyaṃ bhante abbhutaṃ bhante.")               # bhante: the headword's stem is bhante, its lemma bhavant
    kept = Translator._kept_words([u])
    assert kept == {"bhante": "Bhante"} and Translator._address_words([u], kept) == []
    title = _unit(dpd, "Mahānidānasutta", "heading")
    assert Translator._kept_words([title]) == {}                       # a title takes its English in parentheses: it is not "kept bare"


def test_the_backtick_curb_belongs_to_stage_one(dpd, tmp_path):
    from kavi.interlinear import analyse_tokens, backtick_curb, prompt_for
    from kavi.language import set_language
    from kavi.models import review_rules
    text = "Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati. Tatra kho bhagavā bhikkhū āmantesi.\n"
    _, translate, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] x\n[2] y")])
    macro = _discourse_prompt(translate)
    assert backtick_curb() in macro                                    # Stage 1 needs it to keep the model off backticks
    assert "An apostrophe at the start of a word" not in macro         # a Sanskrit avagraha rule: Pāli quotations begin with ‘
    set_language(dpd)
    assert backtick_curb() not in prompt_for("Evaṃ me sutaṃ", analyse_tokens(dpd, "Evaṃ me sutaṃ"), {}, [], initial_draft="x")
    assert backtick_curb() not in review_rules()                       # Stage 2 and the review write technical terms in backticks too


def test_a_backticked_word_with_no_vocative_reading_is_plain_english(dpd, tmp_path):
    from kavi.pipeline import address_keys, unwrap_unlisted
    assert address_keys("'mite") == {"mite", "amite"}                  # the avagraha is often written out
    voc = address_keys("kalyāṇi") | address_keys("'mite")
    text = "You, `kalyāṇi` (good one), are `vatsalā` (tender) and `amite` (immeasurable)."
    assert unwrap_unlisted(text, voc) == "You, `kalyāṇi` (good one), are tender and `amite` (immeasurable)."
    res, _, _ = _fake_run(dpd, tmp_path, "Yadā have pātubhavanti dhammā,\nĀtāpino jhāyato brāhmaṇassa.\n", [
        ("Translate the following", "[1] When indeed phenomena appear,\n[2] to the ardent `jhāyato` (meditating) brahmin.")])
    assert res.units[1].initial_draft == "to the ardent meditating brahmin."


def test_the_discourse_prompt_glosses_each_particle_in_place(dpd, tmp_path):
    text = "Atha kho bhagavā evaṃ eva bhikkhū āmantesi.\n\nSo pi gacchati.\n\nIdaṃ vuccati nāmaṃ.\n"
    _, translate, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] x\n[2] y\n[3] z")])
    prompt = _discourse_prompt(translate)
    assert "[1] Atha kho{indeed} «bhagavā» evaṁ eva{indeed} «bhikkhū» āmantesi." in prompt and "[2] So pi{too / even} gacchati." in prompt
    assert "[3] Idaṁ vuccati nāmaṁ." in prompt                         # the noun nāmaṃ is not the particle "by name"
    assert "each particle is followed by its English in braces" in prompt and "relative pronoun" not in prompt   # only what the text shows


def test_the_braces_offer_english_the_checker_accepts():
    from kavi.language import PARTICLES
    from kavi.lint import PARTICLE_ENGLISH
    for table in PARTICLES.values():
        for stem, english in table.items():
            if stem in PARTICLE_ENGLISH:
                assert set(english.split(" / ")) <= set(PARTICLE_ENGLISH[stem]), stem


@needs_sanskrit
def test_the_discourse_lists_are_precise_about_kinship_adverbs_and_compound_terms(sa):
    from kavi.interlinear import analyse_tokens, terms_of
    u = _unit(sa, "amba tvam asi jananī")                               # amba: a customary form of address, like ārye
    kept = Translator._kept_words([u])
    assert kept["ambā"] == "amba" and Translator._address_words([u], kept) == []      # a vocative stays as it stands, not as its stem
    assert {"niṣprapañca", "prapañca"} <= terms_of(analyse_tokens(sa, "niṣprapañcām"))     # the dictionary gives no members
    assert "bhava" not in terms_of(analyse_tokens(sa, "bhāvena"))       # bhāva's own reading only, not a neighbouring noun
    words = lambda line: [t for t in _unit(sa, line).tokens if not t.punct]
    assert Translator._adverb_only("sukha", words("sukhena gacchati")) and not Translator._adverb_only("sukha", words("sukhaṃ gacchati"))
    assert Translator._glosses(_unit(sa, "api sukham iva paśyati")) == ([("api", "too / even"), ("iva", "like")], [])
    assert Translator._glosses(_unit(sa, "sa naḥ pitā"))[1] == []        # an enclitic reads too many ways to place
    asked = _unit(sa, "tat kiṃ manyase subhūte")                        # subhūte: a vocative, and the dictionary's Subhūti
    kept = Translator._kept_words([asked])
    assert kept.get("subhūti") == "Subhūti" and Translator._address_words([asked], kept) == []
    hymn = [_unit(sa, "tenāpi niyataṃ siddhiḥ prāpyate 'moghadarśane"), _unit(sa, "tena tvam api kalyāṇi sarvasattvapitāmahī")]
    kept = Translator._kept_words(hymn)                                 # a locative by its first reading and a nāga's name: still describing
    assert {"amoghadarśane", "kalyāṇi"} <= set(Translator._address_words(hymn, kept)) and "amoghadarśana" not in kept
    split = [("nāgacchasi", ["na", "āgacchasi"])]
    assert Translator._fusions(_unit(sa, "nāgacchasi kutaś cit tvaṃ")) == split
    assert Translator._fusions(_unit(sa, "nāgacchasi kutaś cit nāgacchasi")) == split      # said twice in a segment: each is split
    assert Translator._fusions(_unit(sa, "sukhenāyānti māyeva dṛśyase")) == []   # a wrong split (ayānti, mai) is not given: a model would obey it
    assert Translator._fusions(_unit(sa, "tvannāthasya na vidyate")) == []        # tvat + nātha is a compound, not two words


def test_a_verse_ends_with_a_full_stop_in_code():
    from kavi.pipeline import close_sentence
    assert close_sentence("Homage to you") == "Homage to you." and close_sentence("Homage to you,;") == "Homage to you."
    assert close_sentence('He says "go."') == 'He says "go."' and close_sentence("Is it so?") == "Is it so?" and close_sentence("") == ""


def test_the_last_line_of_a_verse_is_stopped_and_the_first_is_capitalised(dpd, tmp_path):
    text = "Yadā have pātubhavanti dhammā,\nĀtāpino jhāyato brāhmaṇassa.\n"
    res, _, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] when indeed phenomena appear,\n[2] to the ardent brahmin")])
    assert [u.initial_draft for u in res.units] == ["When indeed phenomena appear,", "to the ardent brahmin."]


def test_the_discourse_prompt_ends_with_the_source_text_and_forbids_o_before_a_word_of_address(dpd, tmp_path):
    text = "Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati. Tatra kho bhagavā bhikkhū āmantesi.\n"
    _, translate, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] x\n[2] y")])
    macro = _discourse_prompt(translate)
    assert macro.rstrip().endswith("Tatra kho{indeed} «bhagavā» «bhikkhū» āmantesi.")     # nothing after the text: a closing line made one model drop its titles
    assert "Never write 'O' before a word of address" in macro and "an unstated subject, 'one'" in macro


def test_a_model_that_copies_the_source_is_told_once_and_a_copy_is_no_draft(dpd, tmp_path):
    from kavi.pipeline import echo_of
    assert echo_of("Yadā have pātubhavanti dhammā", "Yadā have pātubhavanti dhammā,") and not echo_of("Thus heard by me.", "Evaṃ me sutaṃ")
    assert not echo_of("Rāhulabhadra: Prajñāpāramitāstotra", "Rāhulabhadra: Prajñāpāramitāstotra")     # a name or title stays as it is
    text = "Yadā have pātubhavanti dhammā,\nĀtāpino jhāyato brāhmaṇassa.\n"
    copy = "[1] Yadā have pātubhavanti dhammā,\n[2] Ātāpino jhāyato brāhmaṇassa."
    res, translate, _ = _fake_run(dpd, tmp_path, text, [
        ("copies the Pāli text", "[1] When indeed phenomena appear,\n[2] to the ardent meditating brahmin"), ("Translate the following", copy)])
    assert [u.initial_draft for u in res.units] == ["When indeed phenomena appear,", "to the ardent meditating brahmin."]
    again, _, _ = _fake_run(dpd, tmp_path, text, [("copies the Pāli text", copy), ("Translate the following", copy)])
    assert [u.initial_draft for u in again.units] == ["", ""]           # still a copy: no draft, and Stage 2 translates alone


@needs_sanskrit
def test_the_sanskrit_discourse_prompt_marks_words_of_address_and_splits_fused_function_words(sa, tmp_path):
    st = Settings()
    st.use_language("sa")
    st.max_rounds = 0
    st.cache_dir = tmp_path
    translate = FakeModel("Qwen3.8-27B-bf16", [("Translate the following", "[1] x\n[2] y\n[3] z\n[4] for him, `amba` (mother), how\n[5] w")])
    tr = Translator(st, sa, FakePool(translate, FakeModel("x", [])), progress=lambda m: None, use_cache=False)
    res = tr.translate_markdown("kalyāṇi nāgacchasi kutaś cit tvaṃ\nsukhenāyānti māyeva dṛśyase\ntvannāthasya na vidyate\ntasyāmba katham\n"
                                "me tvāṃ paśyati\nyā tvaṃ nirīkṣyase\nsa paśyati tathāgatam\nprajñāpāramite 'mite\n")
    prompt = _discourse_prompt(translate)
    assert "[1] ‹kalyāṇi› na·āgacchasi kutaś cit tvaṃ" in prompt      # marked where it stands; the fused word split in place
    assert "[2] sukhenāyānti māyeva dṛśyase" in prompt and "[3] tvannāthasya na vidyate" in prompt   # no wrong split, no compound
    assert "[4] tasya{of him / that}·«amba» katham" in prompt and "joined by ·" in prompt     # a fused vocative is marked inside the split
    assert "[5] me tvāṃ{you, object} paśyati" in prompt              # an accusative is shown as the object; the enclitic me is not glossed
    assert "[6] yā{who / which} tvaṃ nirīkṣyase" in prompt           # a relative pronoun; the nominative tvaṃ is not glossed
    assert "[7] sa paśyati «tathāgatam»" in prompt and "«like this»" in prompt and "‹like this›" in prompt   # a name is marked in any case
    assert "the English word that carries its case (by, of, to, from, in) is still written" in prompt       # a bare name keeps its "by"
    assert "[8] ‹prajñāpāramite› ‹amite›" in prompt                  # the elided a- is restored in place
    assert "each relative pronoun, and each personal pronoun or tad" in prompt                # the pronoun braces are announced where there are some
    assert "'whatever ... that' only where the relative stands for a thing" in prompt and "written with that word repeated" in prompt
    assert res.units[3].initial_draft == "for him, amba, how"        # a kinship word in backticks with its English stays bare (the surface form)


def test_oblique_pronouns_have_their_english_only_where_it_is_safe():
    from kavi.language import pronoun_english, set_language
    set_language("sa")
    try:
        assert pronoun_english("yuṣmad", "acc", "sg") == "you, object" and pronoun_english("asmad", "loc", "pl") == "in us"
        assert pronoun_english("tad", "gen", "sg", "masc") == "of him / that" and pronoun_english("tad", "gen", "sg", "fem") == "of her / that"
        assert pronoun_english("tad", "instr", "sg") == "by that / therefore" and pronoun_english("tad", "abl", "sg") == "from that / therefore"
        assert pronoun_english("tad", "instr", "sg", "fem") == "by her / that"                # tayā is no "therefore"
        assert pronoun_english("yuṣmad", "nom", "sg") == "" and pronoun_english("tad", "nom", "sg") == ""      # tvam: braces on every one hurt an epithet's form
        assert pronoun_english("yad", "gen", "sg", "masc") == "of whom / of which" and pronoun_english("yad", "nom", "sg", "fem") == "who / which"
        assert pronoun_english("yad", "nom", "sg", "nt") == "" and pronoun_english("yad", "instr", "sg", "masc") == ""   # yad, yena: conjunctions
    finally:
        set_language(None)


def test_what_a_reply_made_of_the_marks_and_braces_is_undone():
    from kavi.pipeline import clean_reply, settle_braces
    assert clean_reply("by «Lokanātha» the ‹kalyāṇi› {you, object} saw you, na·iva {who / which}") == "by Lokanātha the kalyāṇi saw you, na iva"
    glosses = [("tena", "by that / therefore"), ("api", "too / even"), ("yas", "who / which")]
    assert settle_braces("by that therefore you too even, who/which sees", glosses) == "by that you too, who sees"
    assert settle_braces("therefore, by that you even too", glosses) == "therefore, by that you even too"    # only the pairs in the order offered, side by side
    assert settle_braces("who you, object sees; the agent, object and instrument", [("tvāṃ", "you, object")]) == "who you sees; the agent, object and instrument"
    assert settle_braces("the eye of him that, object", [("taṃ", "him / that, object")]) == "the eye of him"


def test_words_of_address_are_marked_in_the_text_and_the_marks_are_not_copied(dpd, tmp_path):
    from kavi.pipeline import gloss_particles, mark_words, split_fused
    assert gloss_particles("tena·api niyataṃ sakṛd apy āśaye", [("api", "too / even"), ("apy", "too / even")]) == "tena·api{too / even} niyataṃ sakṛd apy{too / even} āśaye"
    assert split_fused("tenāpi niyataṃ siddhiḥ", [("tenāpi", ["tena", "api"])]) == "tena·api niyataṃ siddhiḥ"
    assert mark_words("namas tubhyaṃ prajñāpāramite 'mite", {"prajñāpāramite", "amite"}) == "namas tubhyaṃ ‹prajñāpāramite› ‹amite›"
    assert mark_words("kalyāṇinām kalyāṇi", {"kalyāṇi"}) == "kalyāṇinām ‹kalyāṇi›"       # a whole word only
    assert mark_words("sa paśyati tathāgatam kalyāṇi", {"kalyāṇi"}, {"tathāgatam"}) == "sa paśyati «tathāgatam» ‹kalyāṇi›"    # two kinds of mark
    text = "Acchariyaṃ bhante abbhutaṃ bhante.\n\nEvaṃ me sutaṃ.\n"
    res, translate, _ = _fake_run(dpd, tmp_path, text, [("Translate the following", "[1] Wonderful, «bhante», marvellous.\n[2] Thus heard by me {indeed}.")])
    prompt = _discourse_prompt(translate)
    assert "[1] Acchariyaṁ «bhante» abbhutaṁ «bhante»" in prompt and "«like this»" in prompt      # the Pāli prompt shows ṁ
    assert res.units[0].initial_draft == "Wonderful, bhante, marvellous." and res.units[1].initial_draft == "Thus heard by me."


def test_a_thinking_model_gets_room_for_its_reasoning(dpd, tmp_path):
    from kavi.pipeline import THINKING_HEADROOM
    caps = {}
    for thinking in (False, True):
        class Recording(FakeModel):
            def chat(self, messages, **kw):
                if "Translate the following" in messages[-1]["content"]:
                    caps[thinking] = kw["max_tokens"]
                return super().chat(messages, **kw)
        st = Settings()
        st.max_rounds = 0
        st.cache_dir = tmp_path
        st.thinking = thinking
        model = Recording("Qwen3.8-27B-bf16", [("Translate the following", "[1] x\n[2] y")])
        Translator(st, dpd, FakePool(model, FakeModel("x", [])), progress=lambda m: None, use_cache=False).translate_markdown(
            "Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati. Tatra kho bhagavā bhikkhū āmantesi.\n")
    assert caps[True] == caps[False] + THINKING_HEADROOM                 # the reasoning is generated within the same cap


def test_one_addressed_by_a_word_that_is_also_a_name_is_addressed_by_name(dpd, tmp_path):
    from kavi.language import set_language
    set_language(dpd)
    u = _unit(dpd, "Mā hevaṃ, ānanda, avaca.")                         # ānanda: "joy" by the dictionary's first reading, and Ānanda
    kept = Translator._kept_words([u])
    assert kept.get("ānanda") == "Ānanda" and Translator._address_words([u], kept) == []
    town = _unit(dpd, "Kammāsadhammaṃ nāma kurūnaṃ nigamo.")           # nāma: a vocative by its form, and a particle
    assert "nāma" not in Translator._address_words([town], Translator._kept_words([town]))
    assert Translator._address_words([_unit(dpd, "Phassaṃ paṭicca vedanā.")], {}) == []       # paṭicca: an absolutive in the dictionary
    assert "ānanda" not in Translator._kept_words([_unit(dpd, "Ānando jāyati.")])        # not in the vocative: the sentence decides
    _, translate, _ = _fake_run(dpd, tmp_path, "Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca. Kammāsadhammaṃ nāma kurūnaṃ nigamo.\n",
                                [("Translate the following", "[1] x\n[2] y")])
    text = _discourse_prompt(translate).split("Pāli text:")[1]
    assert text.count("hi{for / indeed}·evaṁ, «ānanda», avaca") == 2   # a name's mark; a fused word said twice is split each time
    assert "‹" not in text and "nāma{by name}" in text                 # no describing word; the particle's English


def test_stage1_only_redrafts_what_the_cache_holds(dpd, tmp_path):
    text = "Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati. Tatra kho bhagavā bhikkhū āmantesi.\n"
    answers = [("Translate the following", "[1] At one time the Bhagavā was dwelling at Sāvatthī.\n[2] There indeed the Bhagavā addressed the monks."),
               ("Sentence: Ekaṃ samayaṃ", '{"words": [{"n": 1, "parse": 1, "gloss": "one"}], "translation": "At one time the Bhagavā was dwelling at Sāvatthī."}'),
               ("Sentence: Tatra kho", '{"words": [{"n": 1, "parse": 1, "gloss": "there"}], "translation": "There indeed the Bhagavā addressed the monks."}')]
    st = Settings()
    st.max_rounds = 0
    st.cache_dir = tmp_path
    tr = Translator(st, dpd, FakePool(FakeModel("Qwen3.8-27B-bf16", answers), FakeModel("x", [])), progress=lambda m: None)
    tr.translate_markdown(text)                                        # a full run fills the cache
    assert tr.cache
    again = FakeModel("Qwen3.8-27B-bf16", [("Translate the following", "[1] Draft one.\n[2] Draft two.")])
    res = Translator(st, dpd, FakePool(again, FakeModel("x", [])), progress=lambda m: None).translate_markdown(text, stage1_only=True)
    assert "Draft one." in res.markdown and "Draft two." in res.markdown     # the draft is the output, not the source
    assert len(again.calls) == 1                                       # the discourse call only; the cache is not consulted
