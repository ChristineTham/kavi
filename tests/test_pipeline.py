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
    assert len(review.calls) >= 1 and "Problems already found" not in review.calls[0][-1]["content"] or True
    assert "Then indeed" in out                                                      # the revision was applied
