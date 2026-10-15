
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

def get_symbols(grammar: str):
    if grammar == "in comps":
        return "🆎"

    chunks = grammar.split(' ')
    return ''.join(map(lambda s: to_symbol.get(s, s), chunks))

def get_explanation(grammar: str):
    if grammar[1] == "unknown":
        return f"?({grammar[0]})"
    elif grammar == "particle":
        return "indeclinable or particle"

    chunks = grammar.split(' ')
    return ', '.join(map(lambda s: to_explanation.get(s, s), chunks))

def grammar_parse(grammar: list[tuple[str, str, str]]):
    if grammar[1] == "unknown":
        return f"?({grammar[0]})"
    elif grammar[1] == "particle":
        return f"🔼({grammar[0]})"

    desc = get_symbols(grammar[2])
    if grammar[1] == 'noun':
        desc += f"({grammar[0]})"
    elif grammar[1] == 'verb':
        desc += f"[{grammar[0]}]"
    else:
        desc += f"({grammar[1]}:{grammar[0]})"
    return desc

def grammar_explain(grammar: list[tuple[str, str, str]]):
    if grammar[1] == "unknown":
        return "unknown, possibly a formal name"
    elif grammar[1] == "particle":
        return "particle or indeclinable"
    else:
        return f"{get_explanation(grammar[2])} of \"{grammar[0]}\" ({get_explanation(grammar[1])})"
