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
