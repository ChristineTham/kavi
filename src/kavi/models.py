"""The models and the prompts they are given.

A model is either loaded here with MLX (``MLXModel``: a local folder or a Hugging Face ``org/repo``) or served by a
local Ollama (``OllamaModel``: a name with a tag, ``gemma4:26b-mlx``; see ``ollama.py``); both answer ``chat()`` with
a ``Reply``. ``ModelPool`` hands out one per role, sharing it when the two roles name the same model. The legacy
MITRA pair (``mitra-qwen35-translate`` with its own instruction, ``mitra-qwen35-it`` as reviewer) still runs through
the same pool. Thinking is off unless asked; decoding is greedy with a small repetition penalty.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import ollama
from .dpd import Analysis, analysis_table, reference_pairs, special_words
from .language import LANGUAGE

# --------------------------------------------------------------------------------------
# The model hosts: MLX in this process, Ollama beside it
# --------------------------------------------------------------------------------------


@dataclass
class Reply:
    text: str
    finish_reason: str | None
    tokens: int = 0
    seconds: float = 0.0
    thinking: str = ""


class MLXModel:
    def __init__(self, path: str, log=None):
        from mlx_lm import load
        from mlx_lm.sample_utils import make_logits_processors, make_sampler

        self.path = path
        self.name = Path(path).name
        self._log = log or (lambda msg: sys.stderr.write(msg + "\n"))
        self._log(f"loading {path} …")
        t0 = time.time()
        self.model, self.tokenizer = load(path)
        try:                       # the checkpoint's tokenizer_config says 2048; the model has a 262k context
            self.tokenizer.model_max_length = 1_000_000
        except Exception:
            pass
        self._log(f"  loaded in {time.time() - t0:.1f}s")
        self._make_sampler = make_sampler
        self._make_lp = make_logits_processors

    def chat(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.0,
             repetition_penalty: float = 1.05, thinking: bool = False) -> Reply:
        from mlx_lm import stream_generate

        prompt = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, enable_thinking=thinking)
        out, finish, n = [], None, 0
        t0 = time.time()
        for r in stream_generate(self.model, self.tokenizer, prompt, max_tokens=max_tokens,
                                 sampler=self._make_sampler(temp=temperature),
                                 logits_processors=self._make_lp(repetition_penalty=repetition_penalty)):
            out.append(r.text)
            finish = r.finish_reason
            n += 1
            if _runaway(out):
                finish = "length"
                break
            if _ended(out):
                break
        thought, text = _split_thought("".join(out))
        return Reply(text, finish, n, time.time() - t0, thought)


    def unload(self) -> None:
        """Free the weights."""
        import gc
        del self.model, self.tokenizer
        gc.collect()
        clear_metal_cache()


def _runaway(out: list[str]) -> bool:
    """A model stuck emitting \\u0… escapes."""
    return len(out) >= 16 and "".join(out[-16:]).count("\\u0") >= 4


def _ended(out: list[str]) -> bool:
    """The END line that closes a review answer."""
    return len(out) >= 5 and "\nEND" in "".join(out[-5:])


def _split_thought(text: str) -> tuple[str, str]:
    """(thinking, answer) of a reply that carries its thinking in <think> tags."""
    thought = ""
    m = re.search(r"<think>(.*?)</think>", text, re.S)
    if m:
        thought = m.group(1)
        text = text[m.end():]
    elif "</think>" in text:
        thought, text = text.split("</think>", 1)
    return thought.strip(), text.strip()


class OllamaModel:
    """A model served by a local Ollama, with the interface of ``MLXModel``: the weights live in the server, which
    loads them on the first request and keeps them while the run lasts."""

    def __init__(self, path: str, log=None):
        self.path = path
        self.name = ollama.model_name(path)
        self._log = log or (lambda msg: sys.stderr.write(msg + "\n"))
        why = ollama.problem(path)
        if why:
            raise RuntimeError(why)
        try:
            self._thinks = "thinking" in ollama.call("/api/show", {"model": self.name}).get("capabilities", [])
        except (OSError, ValueError):
            self._thinks = False
        self._log(f"using {self.name} through Ollama at {ollama.host()} …")

    def chat(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.0,
             repetition_penalty: float = 1.05, thinking: bool = False) -> Reply:
        payload = {"model": self.name, "messages": messages, "stream": True, "keep_alive": ollama.KEEP_ALIVE,
                   "options": {"num_predict": max_tokens, "temperature": temperature,
                               "repeat_penalty": repetition_penalty, "num_ctx": ollama.num_ctx()}}
        if self._thinks:                       # a model that cannot think refuses the field
            payload["think"] = bool(thinking)
        out, thought, finish, n = [], [], None, 0
        t0 = time.time()
        with ollama.request("/api/chat", payload, timeout=ollama.read_timeout()) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("error"):
                    raise RuntimeError(f"Ollama: {chunk['error']}")
                msg = chunk.get("message") or {}
                if msg.get("thinking"):
                    thought.append(msg["thinking"])
                if msg.get("content"):
                    out.append(msg["content"])
                    n += 1
                if chunk.get("done"):
                    finish = chunk.get("done_reason") or "stop"
                    n = chunk.get("eval_count") or n
                    break
                if _runaway(out):
                    finish = "length"
                    break
                if _ended(out):
                    finish = "stop"
                    break
        tagged, text = _split_thought("".join(out))
        return Reply(text, finish, n, time.time() - t0, ("".join(thought).strip() or tagged))

    def unload(self) -> None:
        """Ask the server to free the weights now rather than when its keep-alive runs out."""
        try:
            ollama.call("/api/generate", {"model": self.name, "keep_alive": 0}, timeout=30)
        except (OSError, ValueError):
            pass


def clear_metal_cache() -> None:
    """Reclaim freed unified memory buffers from MLX Metal allocator."""
    try:
        import mlx.core as mx
        mx.clear_cache()
        if hasattr(mx, "metal") and hasattr(mx.metal, "clear_cache"):
            mx.metal.clear_cache()
    except Exception:
        pass


class ModelPool:
    """Loads each model once, on first use."""

    def __init__(self, translate_path: str, review_path: str, log=None):
        self.paths = {"translate": ollama.canonical(translate_path), "review": ollama.canonical(review_path)}
        self._models: dict[str, MLXModel | OllamaModel] = {}
        self._log = log

    def get(self, role: str) -> MLXModel | OllamaModel:
        if role not in self._models:
            path = self.paths[role]
            if path in [m.path for m in self._models.values()]:
                self._models[role] = next(m for m in self._models.values() if m.path == path)
            else:
                self._models[role] = (OllamaModel if ollama.is_ollama(path) else MLXModel)(path, self._log)
        return self._models[role]

    def release(self, role: str) -> None:
        """Free a model's weights (two large models may not both fit in memory; the pipeline drops the translator
        before the review phase when the two roles use different models)."""
        m = self._models.pop(role, None)
        if m is None or m in self._models.values():
            return
        m.unload()


# --------------------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------------------

TRANSLATE_HEADER = (
    "You are an expert translator of classical Asian languages. In your translation, make sure to use proper "
    "IAST diacritics if Pāli or Sanskrit terms occur. The translation should be literal and faithful: translate "
    "word by word as far as English allows, render every word of the source and add nothing that is not in it. "
    "Do not explain, interpret or comment, and do not assume the text is religious unless its words say so."
)
REFERENCE_INTRO = (
    " Here is a section of reference translations. Make use of them to improve your translation, but only if "
    "they make sense and really help. Never reproduce them verbatim; always paraphrase them."
)
PLACEHOLDER_NOTE = (
    " The text contains placeholder markers of the form %%number%%. Reproduce every placeholder exactly as it "
    "appears, in the same position relative to the surrounding words, and never translate, renumber or drop one."
)
MARKDOWN_NOTE = " Keep the Markdown formatting of the text (asterisks for bold and italic, line breaks) exactly as it is."


def conventions(specials: dict[str, list[tuple[str, str]]], extra_terms: list[str] | None = None) -> str:
    """The naming and terminology rules, with the words of this text that they apply to."""
    parts = [
        "Leave personal names, place names, titles of texts and honorifics untranslated, in their " + LANGUAGE["name"] + " stem form"
        " with IAST diacritics.",
    ]
    names = specials.get("name", []) + specials.get("honorific", [])
    if names:
        stems = sorted({stem for _, stem in names})
        parts.append("Names and honorifics in this text: " + ", ".join(stems) + ".")
    terms = specials.get("technical", [])
    glosses = sorted({g for _, g in terms} | set(extra_terms or []))
    if glosses:
        parts.append(
            "Where a word is used as a technical term, keep it in " + LANGUAGE["name"] + " in backticks with a short English gloss in "
            "parentheses on its first occurrence, like `khandha` (aggregate); where it is used in its ordinary sense, "
            "translate it plainly. Candidates in this text: " + ", ".join(glosses) + "."
        )
    return " ".join(parts)


def is_mitra_translate(model_path: str) -> bool:
    name = Path(model_path).name.lower()
    return "mitra" in name and "translate" in name


Context = list[tuple[str, str]]   # (previous Pāḷi segment, its translation)


def translate_prompt(source: str, analyses: list[Analysis], has_placeholders: bool, markdown: bool,
                     target: str = "English", extra_terms: list[str] | None = None,
                     glossary: dict[str, str] | None = None, context: Context | None = None) -> str:
    """The MITRA-QWEN translate model's own instruction, with the DPD analysis as in-context reference lines and the
    preceding segments' translations first among them, so that a repeated formula is rendered the same way."""
    header = TRANSLATE_HEADER + " " + conventions(special_words(analyses, glossary), extra_terms)
    pairs = list(context or []) + reference_pairs(analyses, glossary=glossary)
    if pairs:
        header += REFERENCE_INTRO + (" The first reference lines are the preceding sentences of this very text with their "
                                     "translations: keep their renderings for the words and formulas they share with the "
                                     "text to translate.\n" if context else "\n")
        header += "\n".join(f"{s} Means in {target}: {t}" for s, t in pairs)
    if has_placeholders:
        header += PLACEHOLDER_NOTE
    if markdown:
        header += MARKDOWN_NOTE
    return (
        f"{header}\n"
        f"Here is a piece of text to translate: {source}\n"
        f"Provide only the translation, without any explanation or additional information. "
        f"Provide your translation in {target}:"
    )


GENERIC_SYSTEM = (
    "You translate the source language (Pāli or Sanskrit) into English literally and faithfully, word by word as far as English allows. You render "
    "every word in the grammatical form the dictionary analysis gives (case, number, tense, person, voice), keep the "
    "source word order where English allows, and add nothing that is not in the source: no explanation, no commentary, "
    "no interpretation, and no assumption that the text is religious unless its words say so. You answer with the "
    "translation only."
)


def translate_messages_generic(source: str, analyses: list[Analysis], has_placeholders: bool, markdown: bool,
                               extra_terms: list[str] | None = None, glossary: dict[str, str] | None = None,
                               context: Context | None = None) -> list[dict]:
    """A chat prompt for any instruction-following model: the word analysis as a table, the conventions, the text."""
    specials = special_words(analyses, glossary)
    names = sorted({r for _, r in specials.get("name", [])})
    honorifics = sorted({r for _, r in specials.get("honorific", [])})
    terms = sorted({r for _, r in specials.get("technical", [])} | set(extra_terms or []))
    rules = [
        "Render every word; drop no particle (ca, vā, pi, eva, hi, kho, pana, iti are all rendered).",
        "Leave personal names, place names and titles of texts untranslated in their stem form" + (": " + ", ".join(names) if names else "") + ".",
        "Leave honorifics and titles of persons untranslated exactly as they stand in the text" + (": " + ", ".join(honorifics) if honorifics else "") + ".",
        "Where a word is used as a technical term, keep it as it stands in the text in backticks with a short English "
        "gloss in parentheses on its first occurrence, like `viññāṇaṃ` (consciousness), and use the plain gloss afterwards"
        + ("; candidates in this text: " + ", ".join(terms) if terms else "") + ".",
    ]
    if has_placeholders:
        rules.append("Reproduce every %%number%% placeholder exactly, in the same position relative to the surrounding words.")
    if markdown:
        rules.append("Keep the Markdown formatting (asterisks, line breaks) exactly as it is.")
    if context:
        rules.append("Render the words and formulas this text shares with the preceding segments exactly as they were rendered there.")
    user = (
        ("Preceding segments of the same text and their translations:\n" + "\n".join(f"- {s}\n  → {t}" for s, t in context) + "\n\n" if context else "") +
        "Translate this " + LANGUAGE["name"] + " into English.\n\n" + LANGUAGE["name"] + ":\n" + source +
        "\n\nDictionary analysis of every word (headword, part of speech, grammatical form, meanings):\n"
        + analysis_table(analyses) + "\n\nRules:\n" + "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
        + "\n\nAnswer with the translation only."
    )
    return [{"role": "system", "content": GENERIC_SYSTEM}, {"role": "user", "content": user}]


def translate_messages_revision(source: str, analyses: list[Analysis], current_translation: str,
                                issues: list[str], has_placeholders: bool, markdown: bool,
                                extra_terms: list[str] | None = None, glossary: dict[str, str] | None = None,
                                context: Context | None = None) -> list[dict]:
    """A chat prompt asking the translate model to revise its translation in light of reviewer critique."""
    specials = special_words(analyses, glossary)
    names = sorted({r for _, r in specials.get("name", [])})
    honorifics = sorted({r for _, r in specials.get("honorific", [])})
    terms = sorted({r for _, r in specials.get("technical", [])} | set(extra_terms or []))
    rules = [
        "Refinement, not replacement: Refine the previous draft translation, addressing the issues below without discarding the draft's natural English fluency and sentence structure.",
        "Ordinary words are translated into plain English, never left in " + LANGUAGE["name"] + " or given a gloss in parentheses.",
        "Address and fix EVERY issue identified by the reviewer below.",
        "Render every word; drop no particle (ca, vā, pi, eva, hi, kho, pana, iti are all rendered).",
        "Leave personal names, place names and titles of texts untranslated in their stem form" + (": " + ", ".join(names) if names else "") + ".",
        "Leave honorifics and titles of persons untranslated exactly as they stand in the text" + (": " + ", ".join(honorifics) if honorifics else "") + ".",
        "Where a word is used as a technical term, keep it as it stands in the text in backticks with a short English "
        "gloss in parentheses on its first occurrence, like `term` (gloss), and use the plain "
        + ("term" if LANGUAGE["code"] == "sa" else "gloss") + " afterwards"
        + ("; candidates in this text: " + ", ".join(terms) if terms else "") + ".",
        "Never include raw grammatical metadata like [neuter nominative plural] or literal tags like (past).",
    ]
    if has_placeholders:
        rules.append("Reproduce every %%number%% placeholder exactly, in the same position relative to the surrounding words.")
    if markdown:
        rules.append("Keep the Markdown formatting (asterisks, line breaks) exactly as it is.")
    if context:
        rules.append("Render the words and formulas this text shares with the preceding segments exactly as they were rendered there.")
    user = (
        ("Preceding segments of the same text and their translations:\n" + "\n".join(f"- {s}\n  → {t}" for s, t in context) + "\n\n" if context else "") +
        "Revise the translation of this " + LANGUAGE["name"] + " text into English, fixing every issue found by the reviewer.\n\n" +
        LANGUAGE["name"] + ":\n" + source + "\n\n" +
        "Previous draft translation:\n" + current_translation + "\n\n" +
        "Reviewer critique (issues to correct):\n" + "\n".join(f"- {iss}" for iss in issues) + "\n\n" +
        "Dictionary analysis of every word:\n" + analysis_table(analyses) + "\n\n" +
        "Rules:\n" + "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1)) +
        "\n\nProvide the complete revised translation only, with no commentary or explanation."
    )
    return [{"role": "system", "content": GENERIC_SYSTEM}, {"role": "user", "content": user}]


REVIEW_SYSTEM = (
    "You are a meticulous reviewer of translations from Pāli and Sanskrit into English. You check a draft translation word by word "
    "against the source and against a dictionary analysis of every word (part of "
    "speech, grammatical form and meanings), and you correct only what is wrong."
)

def review_rules() -> str:
    """The rules the reviewer checks, in the language of the text: no text's own words in them, the terms from
    the glossary and the analysis that follow."""
    lang = LANGUAGE["name"]
    after = ("is written as the plain term afterwards" if LANGUAGE["code"] == "sa" else "is rendered by the plain gloss afterwards")
    return f"""Rules for the translation:
1. Literal and faithful: every {lang} word is rendered, in the grammatical form the analysis gives (case, number, tense, person, voice); nothing is added, nothing is left out, nothing is paraphrased away. Where the dictionary offers several meanings, the one the sentence needs is chosen; a wrong homonym is an error.
2. No commentary, explanation or interpretation, and no assumption that the text is religious unless its words say so.
3. Refinement, not replacement: correct only specific errors of meaning, case, tense or terminology; keep the draft's natural English sentence structure where it is right. An idiom is rendered by the English it expresses, never by a grammatical tag in brackets or parentheses.
4. Personal names, place names and titles of texts stay untranslated in their {lang} stem form; honorifics and titles of persons stay untranslated exactly as they stand in the text, with no explanation in parentheses.
5. A word used as a technical term stays in {lang}, in backticks with a short English gloss in parentheses on its first occurrence, like `term` (gloss), and {after}; a word used in its ordinary sense is translated plainly, never left in {lang}.
6. Particles are rendered, not dropped.
7. Markdown formatting and any %%number%% placeholders stay exactly where they are.
8. Consistency: the same {lang} word is rendered the same way throughout, and the segments read as one continuous text.
9. A segment is revised only for a specific, verified improvement; a segment that is already accurate is repeated unchanged."""


REVIEW_FORMAT = """Answer in exactly this form and nothing else:

ISSUES:
- one line per problem found, naming the segment number, the Pāli word or phrase, what is wrong and the fix
(or the single word "none" if the translation is correct)

REVISED:
[1] the complete revised translation of segment 1
[2] the complete revised translation of segment 2
(one line per segment, every segment repeated even if unchanged, in the same numbering; a segment that contains line breaks keeps them, with the [n] marker only on its first line)

END"""


def review_prompt(segments: list[tuple[str, str]], analyses: list[Analysis], extra_terms: list[str] | None = None,
                  glossary: dict[str, str] | None = None, known: dict[int, list[str]] | None = None) -> str:
    """segments: (pāli source, current translation) in order; known: problems the checker found, per segment."""
    specials = special_words(analyses, glossary)
    lines = [review_rules()]
    names = sorted({r for _, r in specials.get("name", [])})
    honorifics = sorted({r for _, r in specials.get("honorific", [])})
    terms = sorted({r for _, r in specials.get("technical", [])} | set(extra_terms or []))
    if names:
        lines.append("Names in this text (kept in their stem form): " + ", ".join(names) + ".")
    if honorifics:
        lines.append("Honorifics and titles in this text (kept exactly as they stand): " + ", ".join(honorifics) + ".")
    if terms:
        lines.append("Technical-term candidates in this text: " + ", ".join(terms) + ".")
    lines.append("\nDictionary analysis of the words (Digital Pāli Dictionary):\n" + analysis_table(analyses))
    lines.append("\nSegments to check:")
    for n, (src, tr) in enumerate(segments, 1):
        lines.append(f"\nSegment [{n}]\nPāli: {src}\nTranslation: {tr}")
        if known and known.get(n):
            lines.append("Problems already found in segment [%d] — each of these MUST be fixed in the revised text:" % n)
            lines.extend(f"- {k}" for k in known[n])
    lines.append("\n" + REVIEW_FORMAT)
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Output checks
# --------------------------------------------------------------------------------------

SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?")
META_RE = re.compile(
    r"please provide the (?:text|source)|you would like me to translate|(?:i am|i'm) ready to assist|"
    r"provide the source text|as an ai(?: language)? model|i (?:cannot|can't) translate|"
    r"no text (?:has been |was )?provided|provide only the translation|provide your translation in|"
    r"here is a piece of text to translate|expert translator of classical asian languages",
    re.IGNORECASE,
)


def strip_wrapper(text: str) -> str:
    text = re.sub(r"^\s*(?:English\s+)?[Tt]ranslation\s*:\s*", "", text)
    if len(text) > 1 and text[0] == text[-1] and text[0] in "\"'“”":
        inner = text[1:-1]
        if text[0] not in inner:
            text = inner
    return text.strip()


def is_meta(text: str) -> bool:
    return bool(META_RE.search(text))


def is_degenerate(out: str, src: str) -> bool:
    if len(out) > 6 * len(src) + 80:
        return True
    counts: dict[str, int] = {}
    for m in SENTENCE_RE.finditer(out):
        s = m.group(0).strip()
        if len(s) >= 20:
            counts[s] = counts.get(s, 0) + 1
            if counts[s] >= 3:
                return True
    return False


@dataclass
class ReviewResult:
    issues: list[str] = field(default_factory=list)
    revised: dict[int, str] = field(default_factory=dict)
    raw: str = ""
    parsed: bool = False


def parse_review(text: str, n_segments: int) -> ReviewResult:
    res = ReviewResult(raw=text)
    m = re.search(r"ISSUES:\s*(.*?)\n\s*REVISED:\s*(.*?)(?:\n\s*END\b|\Z)", text, re.S | re.I)
    if not m:
        return res
    issues_text, revised_text = m.group(1).strip(), m.group(2).strip()
    issues = [ln.strip().lstrip("-•* ").strip() for ln in issues_text.splitlines() if ln.strip()]
    issues = [i for i in issues if i and i.lower() not in ("none", "none.", "- none", "no issues", "no issues.")]
    # a rambling reviewer writes its deliberation as bullets: keep the lines that name a segment or a source word
    kept = [i for i in issues if len(i) <= 400 and (re.search(r"\[\d+\]|segment \d", i, re.I) or re.search(r"[āīūṃṅñṭḍṇḷśṣṛṝḷḥṁ]", i))
            and not re.match(r"(?i)(let's|actually|wait|however|looking|the (standard|current|previous)|pāli:|sanskrit:|literal:|q:|a:|this (is|looks|implies|translates))", i)]
    res.issues = (kept if kept else issues)[:8]
    current: int | None = None
    buf: dict[int, list[str]] = {}
    for ln in revised_text.splitlines():
        mm = re.match(r"^\s*\[(\d+)\]\s?(.*)$", ln)
        if mm:
            current = int(mm.group(1))
            buf[current] = [mm.group(2)]
        elif current is not None:
            buf[current].append(ln)
    for k, v in buf.items():
        if 1 <= k <= n_segments:
            res.revised[k] = "\n".join(v).strip()
    res.parsed = bool(res.revised)
    return res
