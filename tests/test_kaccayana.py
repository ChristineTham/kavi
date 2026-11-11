"""Tests for the Kaccāyana grammar rule engine (kavi.kaccayana)."""

from kavi.kaccayana import (
    compound_junction_variants_pali,
    decompose_kitaka_pali,
    is_manogana,
    karaka_for_case,
    undo_initial_vuddhi_pali,
    undo_taddhita_pali,
)


def test_manogana_class():
    assert is_manogana("manas")
    assert is_manogana("cetas")
    assert is_manogana("tapa")
    assert is_manogana("teja")
    assert is_manogana("āyu")
    assert not is_manogana("purisa")
    assert not is_manogana("dhamma")


def test_compound_junction_variants():
    # §330 Mahantaṃ mahā vante
    v = compound_junction_variants_pali("mahā", "puriso")
    assert ("mahanta", "puriso") in v

    # §333 Nassa no vā sare ana
    v = compound_junction_variants_pali("a", "kusala")
    assert ("na", "kusala") in v
    v = compound_junction_variants_pali("an", "ariya")
    assert ("na", "ariya") in v

    # §335 Samāsantagatānaṃ kvaci
    v = compound_junction_variants_pali("dhammo", "mahārāja")
    assert ("dhammo", "mahārājan") in v
    v = compound_junction_variants_pali("kalyāṇa", "sakho")
    # check ending match
    v2 = compound_junction_variants_pali("kalyāṇa", "sakha")
    assert ("kalyāṇa", "sakhi") in v2
    v3 = compound_junction_variants_pali("visāla", "akkha")
    assert ("visāla", "akkhi") in v3

    # §197 Mano-gaṇa in compounds
    v = compound_junction_variants_pali("mano", "maya")
    assert ("manas", "maya") in v
    v = compound_junction_variants_pali("ceto", "vimutti")
    assert ("cetas", "vimutti") in v

    # §337 Dīgho (lengthened vowel in prior member)
    v = compound_junction_variants_pali("rājā", "putto")
    assert ("rāja", "putto") in v


def test_undo_initial_vuddhi():
    # §396/§400 Vuddhi reversals
    assert "vasiṭṭha" in undo_initial_vuddhi_pali("vāsiṭṭha")
    assert "saṅghika" in undo_initial_vuddhi_pali("sāṅghika")
    assert "vinateyya" in undo_initial_vuddhi_pali("venateyya")
    assert "kusalla" in undo_initial_vuddhi_pali("kosalla")


def test_undo_taddhita():
    # §350 Ṇika
    cands = undo_taddhita_pali("dhammiko")
    assert any(c.base == "dhamma" and c.suffix == "-ika" for c in cands)

    # §361 Tta, Tā
    cands = undo_taddhita_pali("manussattaṃ")
    assert any(c.base == "manussa" and c.suffix == "-tta" for c in cands)
    cands = undo_taddhita_pali("lahutā")
    assert any(c.base == "lahu" and c.suffix == "-tā" for c in cands)

    # §364 Vantu, Mantu
    cands = undo_taddhita_pali("guṇavā")
    assert any(c.base == "guṇa" and c.suffix == "-vantu" for c in cands)
    cands = undo_taddhita_pali("satimā")
    assert any(c.base == "sati" and c.suffix == "-mantu" for c in cands)

    # §367 Ī
    cands = undo_taddhita_pali("sukhī")
    assert any(c.suffix == "-ī" and c.base in ("sukh", "sukha") for c in cands)

    # §372 Maya
    cands = undo_taddhita_pali("suvaṇṇamayaṃ")
    assert any(c.base == "suvaṇṇa" and c.suffix == "-maya" for c in cands)

    # §393 To & §394 So
    cands = undo_taddhita_pali("sabbato")
    assert any(c.base == "sabba" and c.suffix == "-to" for c in cands)
    cands = undo_taddhita_pali("sabbaso")
    assert any(c.base == "sabba" and c.suffix == "-so" for c in cands)


def test_karaka_roles():
    nom = karaka_for_case("nom")
    assert nom is not None and "kattā" in nom.pali_name and nom.vibhatti_num == 1

    acc = karaka_for_case("acc")
    assert acc is not None and acc.pali_name == "kamma" and acc.vibhatti_num == 2

    inst = karaka_for_case("inst")
    assert inst is not None and "karaṇa" in inst.pali_name and inst.vibhatti_num == 3
    assert "by" in inst.preposition

    dat = karaka_for_case("dat")
    assert dat is not None and dat.pali_name == "sampadāna" and dat.vibhatti_num == 4
    assert "to" in dat.preposition

    abl = karaka_for_case("abl")
    assert abl is not None and abl.pali_name == "apādāna" and abl.vibhatti_num == 5
    assert "from" in abl.preposition

    gen = karaka_for_case("gen")
    assert gen is not None and "sāmī" in gen.pali_name and gen.vibhatti_num == 6
    assert "of" in gen.preposition

    loc = karaka_for_case("loc")
    assert loc is not None and "okāsa" in loc.pali_name and loc.vibhatti_num == 7
    assert "in" in loc.preposition


def test_decompose_kitaka():
    # §527 Anta, Māna
    p = decompose_kitaka_pali("karonto")
    assert any(x.suffix == "-anta" for x in p)
    p = decompose_kitaka_pali("bhavamāno")
    assert any(x.suffix == "-māna" for x in p)

    # §528 Tabba, Anīya
    p = decompose_kitaka_pali("kātabbaṃ")
    assert any(x.suffix == "-tabba" for x in p)
    p = decompose_kitaka_pali("karaṇīyaṃ")
    assert any(x.suffix == "-anīya" for x in p)

    # §531 Aka
    p = decompose_kitaka_pali("dāyako")
    assert any(x.suffix == "-aka" for x in p)

    # §555 Ta, §556 Na
    p = decompose_kitaka_pali("kato")
    assert any(x.suffix == "-ta" for x in p)
    p = decompose_kitaka_pali("chinno")
    assert any(x.suffix == "-na" for x in p)

    # §561 Tuṃ
    p = decompose_kitaka_pali("kātuṃ")
    assert any(x.suffix == "-tuṃ" for x in p)

    # §563 Tvā
    p = decompose_kitaka_pali("katvā")
    assert any(x.suffix == "-tvā" for x in p)
