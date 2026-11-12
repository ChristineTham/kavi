from kavi.models import parse_review


def test_parse_review_filters_rambling():
    text = """ISSUES:
- Segment [1], 'Yāva': the particle is missing; render it as 'as long as'.
- Let's refine the first part.
- Pāli: 'Atthi idappaccayā jarāmaraṇan'ti
- Actually, looking at the context, the pattern is often a question.
- Segment 1, "puṭṭhena satā": 'when asked' is acceptable.

REVISED:
[1] Thus have I heard.

END"""
    r = parse_review(text, 1)
    assert r.parsed and r.revised[1] == "Thus have I heard."
    assert len(r.issues) == 2 and all("Segment" in i for i in r.issues)


def test_parse_review_none():
    r = parse_review("ISSUES:\n- none\n\nREVISED:\n[1] A.\n[2] B.\nEND", 2)
    assert r.parsed and r.issues == [] and r.revised == {1: "A.", 2: "B."}


def test_an_ollama_model_is_told_from_an_mlx_one(tmp_path):
    from kavi.ollama import is_ollama, model_name
    assert is_ollama("gemma4:26b-mlx") and is_ollama("ollama:gemma4") and model_name("ollama:gemma4") == "gemma4"
    assert not is_ollama("mlx-community/Qwen3.8-27B-bf16") and not is_ollama(str(tmp_path)) and not is_ollama("")
    odd = tmp_path / "a:b"                                   # a folder with a colon in its name is still a folder
    odd.mkdir()
    assert not is_ollama(str(odd))


def test_the_ollama_model_reads_a_streamed_chat(monkeypatch):
    import io, json
    from kavi import models, ollama
    sent = {}
    lines = [{"message": {"thinking": "hm"}}, {"message": {"content": "Thus heard "}}, {"message": {"content": "by me."}},
             {"done": True, "done_reason": "length", "eval_count": 7}]

    def fake_request(path, payload=None, timeout=None):
        sent[path] = payload
        return io.BytesIO(b"\n".join(json.dumps(x).encode() for x in lines))

    monkeypatch.setattr(ollama, "problem", lambda m: None)
    monkeypatch.setattr(ollama, "call", lambda path, payload=None, timeout=10: {"capabilities": ["completion", "thinking"]})
    monkeypatch.setattr(ollama, "request", fake_request)
    pool = models.ModelPool("gemma4:26b-mlx", "gemma4:26b-mlx", log=lambda m: None)
    m = pool.get("translate")
    assert isinstance(m, models.OllamaModel) and pool.get("review") is m           # one model for both roles
    r = m.chat([{"role": "user", "content": "x"}], max_tokens=64, temperature=0.0, thinking=False)
    assert (r.text, r.finish_reason, r.tokens, r.thinking) == ("Thus heard by me.", "length", 7, "hm")
    p = sent["/api/chat"]
    assert p["model"] == "gemma4:26b-mlx" and p["think"] is False and p["options"]["num_predict"] == 64
    assert p["options"]["num_ctx"] >= 8192                                          # never Ollama's small default window
