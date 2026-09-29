from kavi.sandhi import split

KNOWN = {"tattha", "iti", "hoti", "kiṃ", "idha", "evaṃ", "tatra", "ayaṃ", "yathā", "idaṃ", "na", "upeti", "bandhussa", "iva",
         "puna", "eva", "ajja", "agge", "su", "akkhāto", "pati", "uttaritvā", "ati", "antaṃ", "abhi", "udaya", "cakkaṃ", "ca",
         "buddha", "vacanaṃ", "pamādo", "saṃ", "tam", "ahaṃ", "taṃ", "te", "assa", "kho", "so"}


def known(w):
    return w in KNOWN


def first(word):
    r = split(word, known)
    return " + ".join(r[0]) if r else None


def test_iti():
    assert first("tattheti") == "tattha + iti"
    assert first("hotīti") == "hoti + iti"
    assert first("kinti") == "kiṃ + iti"


def test_vowel_sandhi():
    assert "tatra + ayaṃ" in [" + ".join(p) for p in split("tatrāyaṃ", known)]
    assert "bandhussa + iva" in [" + ".join(p) for p in split("bandhusseva", known)]
    assert "na + upeti" in [" + ".join(p) for p in split("nopeti", known)]


def test_agama_and_cc():
    assert "puna + eva" in [" + ".join(p) for p in split("punareva", known)]
    assert "ajja + agge" in [" + ".join(p) for p in split("ajjatagge", known)]
    assert "pati + uttaritvā" in [" + ".join(p) for p in split("paccuttaritvā", known)]
    assert "su + akkhāto" in [" + ".join(p) for p in split("svākkhāto", known)]


def test_compound_and_doubling():
    assert "buddha + vacanaṃ" in [" + ".join(p) for p in split("buddhavacanaṃ", known)]
    assert "idha + pamādo" in [" + ".join(p) for p in split("idhappamādo", known)]
    assert "taṃ + ahaṃ" in [" + ".join(p) for p in split("tamahaṃ", known)]
