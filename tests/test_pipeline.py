"""The pipeline without models: a fake pool returns canned drafts and reviews, so the segment → checker →
review → render loop can be tested offline."""
import pytest
from kavi.config import Settings
from kavi.dpd import DPD
from kavi.models import Reply
from kavi.pipeline import Translator

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
    assert default_model() == DEFAULT_MODEL == "gemma4:26b-mlx" and is_ollama(default_model())
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
    prompt = next(c[-1]["content"] for c in translate.calls if "Translate the following" in c[-1]["content"])
    g = Settings().glossary_map
    assert f"dukkha -> {g['dukkha']}" in prompt and "saṅkhāra -> mental construction" in prompt
    assert "Heart" not in prompt and "sarvajña" not in prompt        # no other text's words, no other language's terms


def test_the_gate_judges_the_output_not_a_list_of_phrases():
    from kavi.pipeline import is_strictly_better
    ok, _ = is_strictly_better("He went to the three realms of existence.", "He went to three realms.", "He went to the three realms.", [], {})
    assert ok
    ok, why = is_strictly_better("He [masculine nominative singular] went.", "He went.", "He went.", [], {})
    assert not ok and "grammatical" in why
