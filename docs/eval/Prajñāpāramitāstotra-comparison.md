# The five models compared on the Prajñāpāramitāstotra: Stage 1 drafts on the final prompt (2026-11-13)

The final outputs of the models that came through the prompt loops (`Prajñāpāramitāstotra-stage1-loops.md`) were graded
line by line against the reference translation (`Prajñāpāramitāstotra-ref.md`) and the Sanskrit. On accuracy and consistency
the first place is gemma4:31b-mlx; with the timings beside it the author chose **qwen3.8:27b-mlx** as the default model, for
its speed (2026-11-14), in place of gemma4:26b-mlx.

## Method

- What was graded: `Prajñāpāramitāstotra-<model>-final.md`, one Stage 1 draft per model on the same final prompt, kavi's
  standard settings (thinking off, temperature 0). 42 verse lines each.
- One grader for all five drafts, a model (Claude Fable 5.2) and not the author, with the model names hidden behind shuffled
  labels; the key was opened only after all 210 verdicts were written down.
- Verdict per line: **right** (the sense is right, nothing dropped or invented, conventions kept; wording that differs from the
  reference but is equally correct counts); **minor** (one small slip: a particle dropped or given the wrong nuance, one word
  a little off, a generation or number wrong); **major** (the construction or a key word is wrong: the line misleads);
  **convention** (the sense is right but a rule is broken: "O", a name translated or in the wrong number). A line is also
  marked **rough** when it is not readable English (a word-order gloss, no articles or commas, hyphenated calques).
- Calls applied to every draft alike: "by that" for the correlative tena is accepted (the prompt's own hint offers it); "the
  perfection of wisdom" for prajñāpāra- in the last line is accepted; the adjectives of line 3 standing before "who sees you"
  are accepted (every draft has them so); bāla as "children" is a minor slip.
- A second run of the two best was graded the same way, to see whether the order holds from run to run.

## Result

| Model | Right | Minor | Major | Convention | No major error | Right and readable | Rough lines |
|---|---|---|---|---|---|---|---|
| gemma4:31b-mlx | 23 | 12 | 6 | 1 | 36 | 23 | 0 |
| muse-glimmer:30b-mlx | 26 | 6 | 8 | 2 | 34 | 18 | 12 |
| qwen3.8:27b-mlx | 22 | 5 | 14 | 1 | 28 | 21 | 1 |
| nemotron-3.5-super:120b | 21 | 8 | 13 | 0 | 29 | 2 | 35 |
| gemma4:26b-mlx (the default until now) | 16 | 6 | 20 | 0 | 22 | 16 | 0 |

Second run, same prompt: gemma4:31b-mlx gave the same draft byte for byte; muse-glimmer:30b-mlx gave a different draft
(30 of 42 lines differ) of the same quality: 25 right, 7 minor, 8 major, 2 convention, 17 right and readable.

Rough automatic scores of the same drafts against the reference (chrF / word F1): gemma-31b 64.0 / 71.6, qwen-27b 62.4 / 71.2,
gemma-26b 58.6 / 67.3, muse-30b 56.0 / 66.3, nemotron-120b 47.8 / 61.3. They agree with the grading on the first place and
disagree below it; the grading is the measure.

### The verdicts, by line number

| Model | Right | Minor | Major | Convention |
|---|---|---|---|---|
| gemma-31b | 2, 3, 7, 8, 9, 10, 12, 15, 16, 17, 20, 22, 24, 25, 31–35, 37, 38, 41, 42 | 1, 4, 6, 11, 13, 14, 26, 27, 28, 36, 39, 40 | 18, 19, 21, 23, 29, 30 | 5 |
| muse-30b | 1–4, 6, 8–12, 17, 18, 20, 22, 25–28, 31–35, 38, 41, 42 | 7, 14, 16, 21, 37, 40 | 5, 13, 15, 19, 23, 29, 30, 39 | 24, 36 |
| muse-30b, second run | 2, 3, 4, 6, 8, 10–13, 17, 18, 22, 25–28, 31–35, 38, 39, 41, 42 | 7, 16, 19, 20, 21, 37, 40 | 1, 5, 9, 14, 15, 23, 29, 30 | 24, 36 |
| qwen-27b | 3, 7, 9, 10, 11, 13, 17, 18, 20, 21, 22, 25, 26, 28, 31, 32, 34, 36, 37, 38, 41, 42 | 12, 15, 16, 35, 39 | 1, 2, 4, 5, 6, 8, 14, 19, 23, 27, 29, 30, 33, 40 | 24 |
| nemotron-120b | 1, 3, 8, 10–13, 16, 18, 20, 22, 24, 25, 31–37, 41 | 9, 14, 15, 17, 21, 26, 38, 39 | 2, 4, 5, 6, 7, 19, 23, 27, 28, 29, 30, 40, 42 | |
| gemma-26b | 1, 2, 8, 9, 10, 12, 20, 24, 25, 28, 31, 33, 36, 37, 41, 42 | 3, 11, 13, 16, 34, 35 | 4–7, 14, 15, 17, 18, 19, 21, 22, 23, 26, 27, 29, 30, 32, 38, 39, 40 | |

Wrong in every draft: line 19 (the dewdrops of the simile are lost or misread), 23 (the compound "having you as nātha" is read
as "your lord"), 29 and 30 (the accusative "you" is made the subject: "you are bound" for "seeing you, one is bound") and 40
(the desiderative "wishing to praise"). Line 5 is wrong or off in every draft because the lexicon does not split the word in
which ārye is fused, so it is never marked or kept bare.

## The models, each in a few lines

- **gemma4:31b-mlx.** The fewest lines that mislead (6), and every line is an English sentence with its punctuation. Its slips are
  small and of the kind Stage 2 and the checker correct: a particle dropped (11, 26, 28), a word a shade off (the first epithet as
  "non-dual", bhāvena as "by essence", "you even" for "you too"). Its worst line is 21, where terror became "consolation". All
  eight describing epithets in form, names bare. The same draft twice running. 93 to 147 seconds for this hymn in ten runs of the
  day (one further run took 426).
- **muse-glimmer:30b-mlx.** The most lines fully right (26 and 25), with the right word where others miss it ("with feeling",
  "wise ones"). But a third of its lines are glosses rather than sentences ("Compassion-natured having taken refuge in you with
  Buddha-dharma in front"), it writes "O amba" and a plural name in the singular, one of its three runs on the final prompt fell
  into a loop (it repeated four segments until the token limit), and its time varies from 90 to 330 seconds.
- **qwen3.8:27b-mlx.** Fluent and fast (about 50 to 80 seconds), but more than twice gemma-31b's misleading lines: a passive read as a
  future ("you will observe"), "it is prohibited" for "resorted to", "O teacher", "indifferent" for the first epithet.
- **nemotron-3.5-super:120b.** Finds many of the words (21 lines right in sense) but writes them in Sanskrit order with hyphens
  ("Space like unstained proliferationless letterless"): two lines of 42 are readable English. 79 GB resident. It also copied
  the prompt's hints into its text until the code learnt to remove them.
- **gemma4:26b-mlx.** The fastest by far (18 to 48 seconds) and fluent, but 20 of 42 lines mislead: "the ocean of the Buddha-dharma",
  "great-grandfather of all beings", "mother of those who seek refuge" for both the producer of terror and the producer of
  reassurance, an epithet of another verse inserted in line 18.
- **nemotron-3.5-lightning:30b-mlx** is not in the table: it copies the Sanskrit instead of translating (see the loops document).

## The decision

The Stage 1 draft is the base the later stages work from: a line that is slightly off is corrected by the word-by-word stage and
the checker, a line that misleads is carried forward, and a draft that is not English or does not arrive costs a rerun. So the
order of the criteria was: lines that mislead (fewest), then readable English, then reliability, then speed and memory.

gemma4:31b-mlx is first on the first three. muse-glimmer:30b-mlx has two or three more lines fully right, which is inside the
run-to-run difference of about three lines, and loses on each of the other criteria. On that order of criteria the grader's
choice was gemma4:31b-mlx, and it was the default for a few hours.

The author's decision, with the timings of the next section in hand: **qwen3.8:27b-mlx** (`DEFAULT_MODEL` in `src/kavi/config.py`).
It writes the draft in half gemma4:31b-mlx's time with nearly as many lines right (22 against 23); the price is the lines that
mislead (14 against 6), which the later stages and the hand correction have to catch. `--model gemma4:31b-mlx` gives the most
careful draft, `--model gemma4:26b-mlx` the fastest (a fifth of gemma4:31b-mlx's time, 20 lines that mislead).

## Speed, tokens and consistency

From the runs already recorded, with no new run: every Stage 1 run of the day was timed and its output tokens counted (40 runs of
these five models, and 11 of nemotron-3.5-lightning). Each run is one model call for the whole hymn (44 segments), and each started
cold (the model was unloaded between runs), so every time includes loading the weights; inside one long run only the first call
pays that. The machine was doing other work at times: the same model's time varies up to two-fold, once four-fold. The prompt is the
same 9,900 characters for every model; its token count was not recorded.

### Speed

| Model | Runs timed | Seconds per draft, median (range) | Output tokens a second | Time against gemma-31b |
|---|---|---|---|---|
| gemma4:26b-mlx | 9 | 20 (18–45) | 52 | 0.2 |
| qwen3.8:27b-mlx | 3 (and one that wrote its answer twice) | 46 (44–79; 134 the doubled one) | 21 | 0.5 |
| nemotron-3.5-super:120b | 10 | 61 (53–109) | 14 | 0.6 |
| gemma4:31b-mlx | 11 | 98 (91–145, once 422) | 10 | 1 |
| muse-glimmer:30b-mlx | 5 (and one failed) | 117 (84–317) | 19, but see below | 1.2 |

The one timing of all three stages (the 105-word Pāli sample, six model calls): gemma4:31b-mlx 906 seconds, gemma4:26b-mlx 184.

### Tokens

| Model | Output tokens for the draft (range over its runs) | Characters per token | Output tokens per line right and readable |
|---|---|---|---|
| gemma4:31b-mlx | 968 (959–1,014) | 3.5 | 42 |
| qwen3.8:27b-mlx | 955 (934–955; 1,883 when it answered twice) | 3.4 | 45 |
| gemma4:26b-mlx | 1,002 (1,002–1,062) | 3.4 | 63 |
| muse-glimmer:30b-mlx | 2,271 (1,709–2,503) | 1.3 | 126 |
| nemotron-3.5-super:120b | 853 (776–853) | 3.4 | 426 |

muse-glimmer's tokeniser spends about two and a half times the tokens on the same English, so its 19 tokens a second is no more
text a second than gemma4:31b-mlx's 10, and its draft uses three quarters of the call's token limit (3,018, set at six tokens a
source word) where the others use a third.

What a minute buys, on the final draft's grades: lines right and readable per minute of model time are 48 for gemma4:26b-mlx, 28
for qwen3.8:27b-mlx, 14 for gemma4:31b-mlx, 9 for muse-glimmer and 2 for nemotron-3.5-super; lines with no major error per minute are
66, 37, 22, 18 and 29.

### Consistency

| Model | Runs | Failed | The same prompt run again | Rough score (chrF) over its runs |
|---|---|---|---|---|
| gemma4:31b-mlx | 11 | 0 | 2 runs: the same draft byte for byte | 61.1–64.2 over ten prompt versions |
| qwen3.8:27b-mlx | 4 | 0 (the first wrote its answer twice, once in the thinking channel) | not repeated; 62.2, 62.2 and 62.4 on its last three prompt versions | 60.7–62.4 |
| gemma4:26b-mlx | 9 | 0 | 2 runs in the earlier loop: 23 of 42 lines differed | 56.6–60.4 |
| nemotron-3.5-super:120b | 10 | 0 | 2 runs: 34 of 42 lines differ (one graded); epithets in form fell from 6 of 8 to 1 with one prompt change | 44.3–47.8 |
| muse-glimmer:30b-mlx | 6 | 1 (a repetition loop to the token limit) | 3 runs: one failed, the other two differ in 30 of 42 lines and grade alike (26 and 25 right) | 55.0–59.0 |
| nemotron-3.5-lightning:30b-mlx | 11 | 8 (copied the source, or reasoned without answering) | 3 runs on the one prompt that worked: all different | 49.0–50.0 on those three |

### What this adds to the decision

gemma4:31b-mlx is the most consistent (no failure in eleven runs, the same draft on a repeat, which also makes a rerun of kavi
reproducible) and the most economical in tokens per good line, and it is the slowest of the four usable models: five times
gemma4:26b-mlx's time and twice qwen3.8:27b-mlx's. qwen3.8:27b-mlx is the efficient middle: half gemma4:31b-mlx's time for nearly
as many lines right (22 against 23), at more than twice the lines that mislead (14 against 6). gemma4:26b-mlx gives the most per
minute and the most lines that mislead (20). On the order of criteria above (misleading lines first) the choice is
gemma4:31b-mlx; the author put time first and chose qwen3.8:27b-mlx.

## The full-pipeline check

Everything above is Stage 1. Before the default was first changed, both gemma models were put through all three stages (discourse
draft, word-by-word analysis in JSON, one review round) on the 105-word Pāli sample `tests/samples/dn15-short.md`, with the cache
off. Both completed: five segments, six model calls, no answer rejected, no finding left open. gemma4:31b-mlx took 906 seconds,
gemma4:26b-mlx 184. The outputs were read, not graded: gemma4:31b-mlx's is the better one there too (Ānanda's "yet for me it
appears plainly obvious", where gemma4:26b-mlx has "it also wears me down like a child of high and low status" and leaves
inflected forms such as "Bhagavanta" and "ānando" in the English). This shows that gemma4:31b-mlx works in the later stages
and in Pāli; it is not a measurement of quality there.

qwen3.8:27b-mlx, the default now, was put through the same check afterwards, with every model call recorded. It completed in
206 seconds (four model calls, 4,486 output tokens, no text in the thinking channel), and it showed three things that are
wrong, none of them the model's own:

- **A name lost.** In the first paragraph the four vocatives of Ānanda came out as "`nāma` (name) ... name". The Stage 1
  prompt offers `ānanda` and the particle `nāma` as possible *describing* words of address and marks them so in the text: the
  list of such words was worked out on the Sanskrit hymn, where the lexicon's first reading as a vocative singular was enough.
  In Pāli the Digital Pāḷi Dictionary's first reading of `ānanda` is the common noun and `nāma` is also a vocative by form. The
  two gemma models ignored the marks there; qwen3.8:27b-mlx obeys what stands on the word, which is the behaviour the loops
  were built on. (The model's replies were not kept, only their sizes, so the step from the marked word to "name" is inferred
  from the prompt and the output.)
- **The review cut off.** The reviewer's reply ran into its limit of 512 tokens and could not be parsed, so the review round
  changed nothing (the two gemma models' reviews fitted).
- **A whole paragraph as one unit.** The sample's numbered paragraphs ("95.", "96.") are taken as list items, one unit each, and
  the word-by-word answer for the first (about 60 words) ran into its limit of 2,776 tokens.

The first was mended the same day (`_name_in_address` and `_address_words` in `src/kavi/pipeline.py`): a word of the text whose
first reading is a vocative singular and whose stem the dictionary also knows as a name is kept as a name (`ānanda`; in
Sanskrit `subhūte`), and a word the dictionary also knows as a particle or an absolutive (`nāma`, `vata`, `paṭicca`) is not
offered as a describing word of address. Checked without a model: the Pāli samples' prompts now mark «ānanda» as a name and
offer none of those words, and the hymn's Stage 1 prompt is byte for byte what it was, so the drafts compared above stand.
Still offered in the Pāli samples, wrongly: three forms in -e that are accusatives or locatives (`pariggahe`, `upādāne`,
`pañcavaggiye`) and one part of a wrongly cut junction (`jara` from `jarāpi`). The second and third findings are untouched.

## Caveats

- One hymn of 42 lines, one reference, one grader who is a model and not the author; the author's reading of the drafts decides.
- Stage 1 only, apart from the short check above: no text has been run through all three stages and graded.
- Every model ran with thinking off, kavi's setting. A reasoning pass might change the order (and the time).
- The prompt was improved in loops on all five models, gemma4:26b-mlx first (the earlier loop) and gemma4:31b-mlx longest (seven
  iterations); it may fit that model best. The reference was written before any of this and none of it was shown to a model.
