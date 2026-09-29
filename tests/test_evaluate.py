from kavi.evaluate import align, chrf, paragraphs, plain, word_f1


def test_plain_and_metrics():
    ref = "3. “And what, bhikkhave, is `paṭiccasamuppādo` (dependent origination)?”"
    same = chrf(ref, ref)
    assert 99.9 < same <= 100.0 and word_f1(ref, ref) == 100.0
    assert plain("`a` **b** [c](x)") == "a b c"
    assert chrf("Thus have I heard.", "Thus I have heard.") > chrf("Homage to him.", "Thus I have heard.")


def test_alignment_by_number():
    cand = paragraphs("3. Alpha.\n\n4. Beta.\n")
    ref = paragraphs("Intro line.\n\n3. Alpha!\n\n4. Beta?\n")
    pairs = align(cand, ref)
    assert [p[0] for p in pairs] == ["3", "4"] and pairs[0][2] == "Alpha!"
