from kavi.segment import parse_markdown, render, split_sentences, protect, restore, placeholders_ok


def test_roundtrip_without_translation():
    text = open("tests/samples/balavatara.md", encoding="utf-8").read()
    blocks = parse_markdown(text)
    assert render(blocks) == text
    kinds = [b.kind for b in blocks]
    assert "heading" in kinds and "table" in kinds and "para" in kinds


def test_paragraph_translation_keeps_prefix_and_breaks():
    text = open("tests/samples/dhp.md", encoding="utf-8").read()
    blocks = parse_markdown(text)
    para = next(b for b in blocks if b.kind == "para")
    assert para.prefix == "> " and para.breaks[0] == "\\" and para.text.count("\n") == 2
    para.translation = "a\nb\nc"
    out = render(blocks)
    assert out.splitlines()[0] == "> a\\" and out.splitlines()[2] == "> c"


def test_sentences():
    s = split_sentences("Ekaṃ samayaṃ bhagavā viharati. Tatra kho bhagavā āmantesi— “Dveme, bhikkhave, antā.” Katame dve?")
    assert len(s) == 3 and s[-1] == "Katame dve?"


def test_placeholders():
    masked, kept = protect("see `sandhi` and [§12](/kaccayana/1-sandhikappa#m12) here")
    assert masked == "see %%0%% and %%1%% here" and restore(masked, kept).startswith("see `sandhi`")
    assert placeholders_ok("voir %%1%% et %%0%%", masked) and not placeholders_ok("voir %%0%%", masked)
