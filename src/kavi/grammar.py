
"""The textbook's symbols for the Digital Pāḷi Dictionary's grammatical terms, and their explanations."""

to_symbol = {
    "nom": "①",
    "acc": "②",
    "instr": "③",
    "dat": "④",
    "abl": "⑤",
    "gen": "⑥",
    "loc": "⑦",
    "voc": "⓪",
    "masc": "🚹",
    "fem": "🚺",
    "nt": "🚻",
    "x": "⚧️",
    "sg": "⨀",
    "pl": "⨂",
    "dual": "⨁",
    "act": "🟢",
    "reflx": "🔵",
    "pr": "▶️",
    "fut": "⏭",
    "aor": "⏮",
    "opt": "⏯",
    "imp": "⏹",
    "cond": "🔀",
    "imperf": "↩️",
    "perf": "🔄",
    "1st": "👆",
    "2nd": "🤘",
    "3rd": "🤟",
}

to_explanation = {
    "1st": "first person",
    "2nd": "second person",
    "3rd": "third person",
    "abbrev": "abbreviation",
    "abhi": "Abhidhamma",
    "abl": "ablative case",
    "abs": "absolutive verb",
    "abstr": "abstract noun",
    "acc": "accusative case",
    "act": "action noun, process noun",
    "adj": "adjective",
    "adv": "adverb",
    "agent": "agent noun",
    "aor": "aorist verb",
    "app": "active past participle",
    "base": "pronominal base",
    "bsk": "Buddhist Hybrid Sanskrit",
    "card": "cardinal number",
    "caus": "causative verb",
    "comm": "commentary meaning",
    "comp": "compound",
    "comp vb": "compound verb",
    "compar": "comparative adjective",
    "comps": "in compounds, word is only found as an element within compounds",
    "cond": "conditional mood",
    "conj": "conjunction",
    "cs": "conjugational sign",
    "dat": "dative case",
    "deno": "denominative verb",
    "derog": "derogatory",
    "desid": "desiderative verb",
    "dial": "dialectical, non Indo-Aryan word",
    "dimin": "diminutive noun",
    "ditrans": "ditransitive verb",
    "emph": "emphatic particle",
    "excl": "exclamation",
    "fem": "feminine noun",
    "fut": "future tense",
    "gen": "genitive case",
    "gen abs": "genitive absolute construction",
    "ger": "gerund",
    "gram": "grammatical term, technical term",
    "idiom": "idiomatic expression",
    "imp": "imperative mood",
    "imperf": "imperfect past tense",
    "impers": "impersonal",
    "in comps": "in compounds, word is only found as an element within compounds",
    "ind": "indeclinable",
    "inf": "infinitive verb",
    "instr": "instrumental case",
    "intens": "intensive verb",
    "interr": "interrogative pronoun",
    "intrans": "intransitive verb",
    "irreg": "irregular conjugation or declension",
    "lit": "literal meaning",
    "loc": "locative case",
    "loc abs": "locative absolute construction",
    "masc": "masculine noun",
    "matr": "matronymic",
    "neg": "negative",
    "neut": "neuter noun",
    "nom": "nominative case",
    "noun": "noun, substantive",
    "nt": "neuter noun",
    "onom": "onomatopoeia",
    "opt": "optative mood",
    "ordin": "ordinal number",
    "pass": "passive verb",
    "patr": "patronymic",
    "perf": "perfect past tense",
    "pl": "plural number",
    "pos": "part of speech",
    "pp": "past participle",
    "pr": "present tense",
    "prefix": "prefix",
    "prep": "preposition",
    "prk": "Prakrit",
    "pron": "pronoun, pronominal adjective",
    "prp": "present participle",
    "ptp": "potential participle, future passive participle",
    "reflx": "reflexive verb",
    "sandhi": "sandhi compound",
    "sg": "singular number",
    "sk": "Sanskrit",
    "suffix": "suffix",
    "superl": "superlative adjective",
    "trans": "transitive verb",
    "vb": "verb",
    "ve": "verbal ending",
    "voc": "vocative case",
    "wrt": "with regard to",
    "x": "no gender",
    "dual": "dual",
}

to_meaning = {
    "nom": "subject",
    "acc": "object",
    "instr": "by/with",
    "dat": "for",
    "abl": "from",
    "gen": "of",
    "loc": "in/at/on",
    "voc": "vocative",
}

def get_symbols(grammar: str) -> str:
    """The DPD's grammar abbreviations ("masc nom sg", "pr 3rd sg") as the textbook's symbols, in the DPD's order.
    :mod:`kavi.interlinear` composes them in the textbook's own order (gender, number, ending; voice, number,
    person, tense) from the parsed fields instead."""
    if grammar == "in comps":
        return "🆎"
    return "".join(to_symbol.get(s, s) for s in grammar.split(" "))


def get_explanation(grammar: str) -> str:
    if grammar in ("particle", "ind"):
        return "indeclinable or particle"
    return ", ".join(to_explanation.get(s, s) for s in grammar.split(" "))


def grammar_parse(grammar: tuple[str, str, str]) -> str:
    """(lemma, part of speech, DPD grammar) -> symbols with the lemma: nouns in parentheses, verbs in brackets."""
    lemma, pos, gram = grammar
    if pos == "unknown":
        return f"?({lemma})"
    if pos in ("particle", "ind"):
        return f"⏏️({lemma})"
    desc = get_symbols(gram)
    if pos == "noun":
        return desc + f"({lemma})"
    if pos == "verb":
        return desc + f"[{lemma}]"
    return desc + f"({pos}:{lemma})"


def grammar_explain(grammar: tuple[str, str, str]) -> str:
    lemma, pos, gram = grammar
    if pos == "unknown":
        return "unknown, possibly a formal name"
    if pos in ("particle", "ind"):
        return "particle or indeclinable"
    return f"{get_explanation(gram)} of \"{lemma}\" ({get_explanation(pos)})"
