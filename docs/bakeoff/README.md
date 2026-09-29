# Model bake-off

Same passage for every model: the opening of the Mahānidānasutta (DN 15, tipitaka2500 7D/2/2.1, paragraphs 95
and the first of 96 — `tests/samples/dn15-short.md`), the text the author has translated at
https://christham.net/buddhavacana/sutta/deporig/. Each model was run as **translator** (its own draft, then the
checker) and as **reviewer** (given MITRA-translate's checked draft and the checker's open findings). Machine: M-series
Mac, 64 GB. All non-MITRA models are `mlx-community` 8-bit builds; the MITRA models are bf16.

| model | role | s/paragraph | what happened |
| --- | --- | --- | --- |
| mitra-qwen35-translate (9B bf16) | translate | 14 | fluent, idiomatic; paraphrases ("as plain as the surface of a pond" for `uttānakuttānako viya khāyati`); ignores the naming conventions (Blessed One, Deer Park), drops `kho`, present → past; the checker repairs 4–6 items per paragraph |
| mitra-qwen35-it (9B bf16) | translate | 15 | like the translate model, slightly more literal ("Thus I heard"); invents an idiom ("as clear as clear can be") |
| mitra-qwen35-it (9B bf16) | review | 23 | applies the checker's concrete instructions (2/2) and reports them back; finds nothing of its own; leaves paraphrases alone |
| Qwen3.8-27B-8bit | translate | 56 | the most literal readable draft: keeps Bhagavā/Bhante unaided, renders `kho`, `yāva`, the `iti` marks; glosses every technical term; one grammatical error (`puṭṭhena satā` "to him who exists") |
| Qwen3.8-27B-8bit | review | 133 | applies the instructions but rambles (20 pseudo-issues on one sentence), and "corrects" a wrong idiom into another wrong one ("clear like the sky") |
| gemma-4-26B-A4B-it-qat-8bit (MoE, 4B active) | translate | 11 | fastest; interlinear word salad ("Thus me heard— a certain time Bhagavā in Kurūsu dwells … it eats"), misreads `khāyati` as "eats", hallucinates "bird's nest" |
| gemma-4-26B-A4B-it-qat-8bit | review | 13 | damages the text ("it strives like three [things] in space"), misled by a bad deconstructor split of `khāyatī` (since fixed in the analysis) |
| gemma-4-31B-it-qat-8bit | translate | 62 | literal and rule-following unaided (Bhagavā, Bhante, `dhamma` (teaching) in stem form, particles), no checker fixes needed; stilted ("Thus by me was heard", the yena … tena idiom rendered word for word) |
| gemma-4-31B-it-qat-8bit | review | 96 | applies the checker's instructions (2/2), finds real paraphrases (`uttānakuttānako viya khāyati` → "appears very clear like") and keeps its critique to the point; also flattens the yes/no question `Atthi idappaccayā jarāmaraṇaṃ?` into a statement, as Qwen did |
| any, thinking on | — | 40–420 | the chain of thought streams into the answer and never finishes within 2048–4096 tokens; not usable at this size |

Reports: `1-mitra-qwen38-nothink.md`, `2-gemma26-nothink.md`, `3-qwen38-gemma26-think.md`, `4-gemma31-nothink.md`.

What the runs taught the tooling: the deterministic checker (`lint.py`) now does what no 9B–27B reviewer did
reliably — restores names and honorifics, sets the `word` (gloss) form once, puts a present-tense verb back into
the present, reports dropped particles — and the reviewer is handed those findings as instructions to apply.
The analysis ranks the DPD deconstructor's splits together with the Kaccāyana heuristics (`khāyatī` = `khāyati` +
lengthening, not `khā` + `yatī`) and shows one headword per part of speech so a pronoun sense is never hidden.


## Whole-text runs on DN 15 (33 segments, 1504 words)

| run | configuration | time | character |
| --- | --- | --- | --- |
| A (`../samples/dn15-A-mitra.md`) | MITRA translate → checker → MITRA-it review, 3 rounds | 26 min | fluent; the checker supplies the conventions; the question formulas of §96 drift ("one should say" / "one should answer" / "Does craving exist"); 21 checker findings left open, mostly `kho` |
| B (`../samples/dn15-B-qwen-gemma.md`) | Qwen3.8-27B translate → checker → Gemma 4 31B review, 2 rounds | 89 min | literal and convention-faithful unaided (glossary glosses used: "phenomenal objects"); grammatical slips from over-literal parsing (`puṭṭhena satā` "with a virtuous man being", `asati` "if birth entirely eats", §98 word salad); 12 findings left open |

After run A the pipeline gained two consistency measures: the translate model now sees the preceding two segments
with their translations as its first reference lines, and the checker replaces every other rendering of a glossary
term with the glossary's gloss. Re-run on §96 with the fast configuration (`../samples/dn15-96-consistency-A.md`,
103 s for 6 segments), the formula is identical in all six paragraphs.
