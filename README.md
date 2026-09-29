# Kavi

A literal Pāḷi → English translator that runs entirely on your Mac.

Kavi cuts a Markdown or plain-text document into paragraphs and sentences, resolves every word — sandhi
undone with the [Digital Pāḷi Dictionary](https://www.dpdict.net/)'s deconstructor and the rules of
Kaccāyana's Sandhikappa — looks each word up in the DPD, and hands the word-by-word analysis (part of speech,
grammatical form, meanings) to a translation model as reference material. A second, instruction-following model
then reviews the draft against the Pāḷi and the same analysis and revises it, and a deterministic checker enforces
what a small model forgets: names left untranslated, honorifics kept as they stand, technical terms shown as
`viññāṇaṃ` (consciousness) on first use, particles rendered. The loop runs until the reviewer reports nothing or a
round limit is reached. Markdown structure (headings, lists, blockquotes, tables, inline code, links) survives.

The translation aims to be literal and faithful, word by word as far as English allows, with nothing added and
no assumption that the text is religious unless its words say so.

## Models

| Role | Default | Notes |
| --- | --- | --- |
| translate | [`buddhist-nlp/mitra-qwen35-translate`](https://huggingface.co/buddhist-nlp/mitra-qwen35-translate) | Dharmamitra's 9B Pāḷi/Sanskrit/Tibetan/Chinese translator; the DPD analysis is fed through its in-context reference channel |
| review | [`buddhist-nlp/mitra-qwen35-it`](https://huggingface.co/buddhist-nlp/mitra-qwen35-it) | Dharmamitra's instruction-tuned chat model |
| either | `mlx-community/Qwen3.8-27B-8bit`, `mlx-community/gemma-4-26B-A4B-it-qat-8bit`, `mlx-community/gemma-4-31B-it-qat-8bit` | any MLX chat model can take either role (`--translate-model`, `--review-model`); `tools/bakeoff.py` compares candidates side by side |

Both MITRA models are converted to MLX in bf16 (about 17 GB each). `kavi setup` downloads and converts them
(the checkpoints declare `model_type: qwen3_5_text`, which mlx-lm does not know; setup patches it to `qwen3_5`).

## Data

Kavi needs the DPD's SQLite release `dpd.db` (2.3 GB, CC BY-NC-SA 4.0, Bodhirasa Bhikkhu) and, for sandhi,
`deconstructor_output.json` from the same project, in `./data/` (or `$KAVI_DATA_DIR`, or `$KAVI_DPD_DB`).
Get them from https://github.com/digitalpalidictionary/dpd-db/releases. The JSON is indexed once into
`deconstructor.sqlite` on first use.

## Install and run

```bash
uv sync                                   # Python 3.12, mlx-lm, streamlit
uv run kavi setup                         # download + convert both MITRA models (bf16)
uv run kavi doctor                        # check data and models
uv run kavi translate sutta.md -o sutta.en.md --report review.md --table words.md
uv run kavi translate --text "Ekaṃ samayaṃ bhagavā bārāṇasiyaṃ viharati."
uv run kavi analyse "Tatthodantāsarā aṭṭha."   # the DPD word table only
uv run kavi app                           # Streamlit interface
```

Useful flags: `--rounds N` (review rounds, default 5; `--no-review` for the draft only), `--glossary FILE`
(`term: gloss` lines, default the built-in doctrinal glossary in `src/kavi/glossaries/default.txt`, `none` to
disable), `--sentence-words N`
(paragraphs longer than this are translated sentence by sentence), `--batch-words N` (review batch size),
`--think` (let the reviewer think), `--translate-model`, `--review-model`.

## Which models

`docs/bakeoff/` compares the candidates on the opening of DN 15 (the same text translated by hand at
https://christham.net/buddhavacana/sutta/deporig/). In short:

| configuration | s/paragraph | character |
| --- | --- | --- |
| default: MITRA translate → checker → MITRA-it review | ~40 | fluent and fast; the checker supplies the conventions the models ignore; paraphrases survive |
| `--translate-model Qwen3.8-27B-8bit` | ~60 + review | the most literal readable draft, conventions followed unaided; occasional grammatical slip |
| `--review-model gemma-4-31B-it-qat-8bit` | ~100 per review | the reviewer that both applies the checker's instructions and finds paraphrases of its own |
| Gemma 4 26B-A4B | ~12 | fast but interlinear word salad; not recommended |
| any model with `--think` | minutes | the chain of thought never finishes within the token budget; not usable |

The translate model is released from memory before the review phase when the two roles use different models, so a
27B translator and a 31B reviewer can be combined on a 64 GB machine.

## Measuring and improving

`kavi eval candidate.md reference.md --source pali.md` scores an output against a reference translation: chrF
(character n-gram F-score), word F1, the checker's remaining findings against the source, and how many glossary
terms are rendered as the reference renders them. `tests/samples/sn12-1.md` with `sn12-1.reference.md` (the
author's published translation of the Paṭiccasamuppāda passage) is the first regression sample; `docs/eval/`
keeps the baselines, so a change to a prompt, the checker or a model can be judged by its numbers.

Roadmap for the default configuration, in the order the whole-text runs suggest:

1. a paraphrase detector — English words with no source in the DPD analysis ("surface of a pond") reported to the
   reviewer as findings, the way dropped particles are;
2. a targeted second opinion — only segments with open findings or a low self-consistency score go to Gemma 4 31B;
3. template reuse — a sentence that differs from an earlier one in one or two words takes that sentence's translation
   with the words substituted (the formulaic repetition of the suttas);
4. homonym choice — when the DPD lists several headwords for a form, prefer the one whose part of speech fits the
   neighbouring words (`asati` the participle after a noun, not the verb "eats").

## How it works

1. **Segment** (`segment.py`): Markdown blocks; inline code, links, tags, footnotes and URLs become `%%n%%`
   placeholders that must come back intact.
2. **Analyse** (`dpd.py`, `sandhi.py`): every distinct word is looked up in the DPD `lookup` table; unknown forms
   are split by the deconstructor, then by the reverse-sandhi heuristics (Kaccāyana §12–§50), and the parts looked
   up. Names, honorifics and technical terms are recognised from the DPD's meanings and family sets, the built-in
   glossary and a capitalisation heuristic.
3. **Translate** (`models.py`): MITRA's prompt with `word Means in English: gloss [headword, form]` reference lines,
   or a generic instruction prompt with the analysis table for other models. Long paragraphs go sentence by sentence.
4. **Check** (`lint.py`): deterministic fixes and findings — names restored in stem form ("in Migadāya"),
   honorifics kept as they stand with their article ("the Bhagavā", "bhikkhave"), technical terms given the
   `word` (gloss) form once (the word as it stands when nominative or vocative, otherwise the stem: `viññāṇaṃ`
   (consciousness), `dhamma` (teaching)), a present-tense verb rendered as "was …ing" put back into the present,
   dropped particles reported. What cannot be fixed by string edits is handed to the reviewer as an instruction.
5. **Review** (`pipeline.py`): batches of segments (default up to 400 Pāḷi words) go to the review model with the
   analysis table and the checker's open findings; its `ISSUES` / `REVISED` answer is parsed, checked and applied;
   repeat while something changes and problems remain, up to `--rounds`.

Translations are cached in `~/.cache/kavi/translations.json` by source text and settings.

## Licence

Code: CC0. The DPD is CC BY-NC-SA 4.0 (consulted, not redistributed). MITRA-QWEN is Apache-2.0; if you publish its
output, the model authors ask for a credit to the Dharmamitra project (https://dharmamitra.org).
