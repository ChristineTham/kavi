# The Stage 1 prompt, improved one model at a time: the Prajñāpāramitāstotra loops of 2026-11-13

This records how the Stage 1 (discourse) prompt of `kavi translate --stage1` was improved on the Prajñāpāramitāstotra
by running an improvement loop on each model in turn. It is the history of the changes and the reasons for them. The
comparison of the models' final outputs is in `Prajñāpāramitāstotra-comparison.md`. The earlier loop on gemma4:26b-mlx
is in `Prajñāpāramitāstotra-stage1.md`; its prompt is the starting point of everything below.

## The procedure

- One model at a time, in this order: gemma4:31b-mlx, qwen3.8:27b-mlx, muse-glimmer:30b-mlx, nemotron-3.5-super:120b.
  nemotron-3.5-lightning:30b-mlx was skipped (below). Each loop was finished before the next began.
- One iteration: run the model once on the current prompt (Stage 1 only, kavi's standard settings, thinking off); a
  separate reviewer agent grades the 42 verse lines against the author's reference translation and the conventions
  (OK, SENSE or CONV per line) and judges each earlier change (helped, did nothing, hurt) for that model; the prompt is
  changed on the reviewer's proposals; the same model is run again.
- The prompt is cumulative and never went back to an earlier state except to remove a change shown to hurt. The next
  model's loop started from the prompt the previous loop left.
- A loop was closed by the author when an iteration came back level with the one before it (inside the run-to-run noise of
  about three lines) and the reviewer's remaining proposals were worth about two lines or less. There was no cap on iterations.
- Rules for what goes into the prompt: general only (no word of the hymn), lexicon-generated lists and hints rather than
  described classes, and a proposal backed by one model's evidence about one or two lines waits for a second model.
- Each model's last loop output is `Prajñāpāramitāstotra-<model>.md`; after the last loop all the models that worked were
  run once more on the final prompt: `Prajñāpāramitāstotra-<model>-final.md`.

## What the loops found (read this before reading any draft)

1. A hint shown **in place**, on the word, is obeyed; a list or a description far from the word is obeyed much less. Particles
   in a list in rule 1 were dropped or had two of three glosses written; the same particles with their English in braces
   beside them were rendered almost every time. The same held for marks on words of address, for sandhi splits and for pronouns.
2. A model copies what it is shown: a brace's text ("you, object"), a pair of options ("by that / therefore"), a label, a
   leading apostrophe. Several changes were needed to make a hint safe, and a few hints hurt one model (below).
3. The deterministic code after the reply matters: the raw replies of most models have no verse-final full stops and no capitals
   at a verse start, and several kept a name's English or backticks that the code then removes. Counts of "OK lines" depend
   on that code; a reviewer's grade of a draft is a grade of the mended draft.
4. Part of every iteration-to-iteration change is run-to-run noise (about three lines) even at the same prompt.

## The prompt now

Everything is generated from the lexicon for the chunk in hand; Sanskrit only unless stated.

- Rule 1, in the numbered text, braces after the word: every particle (api "too / even", iva "like", eva "indeed", ca "and",
  vā "or", tu, hi, khalu, kila, nāma, aho, bata; Pāli pi, kho, kira, pana), every relative pronoun (not the neuter yad nor
  yena/yasmāt), every personal pronoun or tad in a case other than the nominative ("you, object", "of him / that", "in you";
  tena/tasmāt "by that / therefore"); and a sandhi-fused word shown split with "·" (vowel junctions of two known words, no
  compounds, no generated readings). The sentence says a brace holds only the English to write.
- Rule 2: the names, titles, honorific stems and kinship words of the chunk to keep bare (a vocative as it stands); a word
  whose first reading is a vocative and whose stem the dictionary also knows as a name counts as a name (Pāli `ānanda`).
- Rule 3: the words that can be words of address (a list); two kinds of mark in the numbered text, «name, title or kinship word»
  (any case; copied bare, the plural with an English -s, the English word that carries its case kept) and ‹describing word›
  (set off by commas, written `word` (English); an elided a- is shown restored); "never 'O'"; the address sentence.
- Rule 4: the glossary renderings of the terms present, including a term inside a compound with the privative nis-/nir-;
  a term whose every occurrence is an adverbial instrumental in -ena is left out.
- Rule 5: formulas, with a conditional correlative sentence. Rule 8: construing hints (passive subject, accusative object,
  repeat the pronoun for adjectives that agree across a half-verse). No closing line after the text.
- Code after the reply: marks, dots, braces and a copied ", object" are removed; a two-option brace written whole is
  collapsed to its first word; a `word` (English) not on the address list is unwrapped; a parenthesis after a kept name (surface
  form or stem) is removed; verse capitals and verse-final full stops are added; a reply that mostly copies the source is
  asked again once and copied lines are dropped. A thinking model gets 12,288 extra tokens for its reasoning.

## What each loop changed, and why

**gemma-31b (seven iterations).** Its first review (original prompt) named glossary-list errors, off-list backticks, kinship
words, dropped particles. Changes, in order: terms inside nis-/nir- compounds listed (prapañca in niṣprapañca) and adverbial
-ena terms left out, a stray noun stem no longer entering the list; a backticked word that is no word of address unwrapped in code;
kinship words kept bare; a per-segment particle list (later moved in place, see above); an address sentence and "never 'O'"; a
verse-final full stop in code (the raw replies had none); the closing instruction after the text removed (it made the model
translate the titles); fused function words listed, then split in place; words of address marked in the text (all 8 epithets
in form from then on); interjections; a conditional correlative sentence; particles with one English word in place;
connectives in place. A repeat-the-pronoun sentence and a passive/accusative hint did nothing for this model and stayed
(other models may need them). The loop was closed when two consecutive iterations were level.

**qwen-27b (two iterations).** The earlier changes worked for it (particles, splits, marks, the address rule; its reply is no
longer generated twice through a thinking channel as it was on the original prompt). Added:
oblique pronouns in place; kinship wording in rule 3; a bug fixed (a kept name written in backticks with its English was
matched by stem only, so a vocative's English replaced the name); relative pronouns in place.

**nemotron-3.5-lightning:30b-mlx (skipped).** In kavi's standard mode (thinking off) it copies every Sanskrit line, and
copied them again when told once to translate; with its own thinking mode it spent 15,306 tokens (54,000 characters of
reasoning, 194 s) without answering. Not run further, at the author's instruction.

**muse-30b (two iterations).** A single mark for two kinds of word confused it (a describing word left bare, a kinship word
written with backticks, names inside inflected forms translated): two kinds of mark (names «», describing words ‹›), and
"set off by commas" in the marks sentence.

**nemotron-120b (three iterations and four ablation runs).** It copied brace text into its English ("you, object"),
lost the English "by" before marked names (a wording of mine: "copied bare, whatever its case"), and left the two
apostrophe-initial epithets without English. Changes: a sentence that a brace holds only the English, with the label
stripped in code; the case word kept with a bare name; tena/tasmāt braced with both options; the elided a- restored in place;
a two-option brace written whole collapsed in code. **Reverted:** braces on every nominative personal pronoun (tvam{you}):
epithets in form fell from 6 of 8 to 1 or 3 of 8, and four short runs with the other changes removed in turn showed that
change alone was the cause.

**The final rerun.** gemma-26b, gemma-31b, qwen-27b, muse-30b and nemotron-120b were each run once more on the final prompt. muse-30b's
first attempt fell into a repetition loop (it translated six segments, then repeated four of them to the token limit) and was not
saved; its second attempt is its `-final` file. The others came through at the first attempt.

## Deferred or rejected, with the reasons

- Rebuilding the title lines in code (the later stages own headings); a mark for adjective-only agreement and an in-place
  agreement hint (one or two lines of one model; needs the lexicon's agreement logic); the parts or dictionary meanings of a
  marked epithet in braces (the dictionary is good where the models are already right and misleading where they are wrong:
  nirvikalpa "not admitting an alternative", bhakti "distribution").
- Compounds shown hyphenated in place; pronoun-initial compounds split (the lexicon's compound splits include wrong ones,
  which would be obeyed: avaśyāyodabindavaḥ as avaśyāyā + udabindavaḥ).
- The English of api chosen by its neighbours, and a restrictive "only" for eva after a pronoun (the reference itself renders
  them by context: even once, too, though, indeed).
- An accusative brace naming its governing verb (the lexicon's readings of participles are unreliable: apaśyann as a finite
  verb, paśyann as a noun); a neuter relative in a verbless reason clause glossed as a conjunction; glossary terms shown in
  place (the false match is a compound member).
- A check after the reply that asks again for a dropped particle (an extra model call: the author's decision).
- The lexicon's split of "cārye" (ca + ārye is read as one word, so ārye is never marked or kept bare): a ranking change that
  needs a full-text scan of the Heart, Diamond and MMK and the author's judgement.

## Caveats

One 42-line text, one reference; reviewers are model agents, not the author; all models run with thinking off, kavi's
default; Stage 2 and the review are untested; the hints are Sanskrit-only where they depend on a table (pronouns, relatives),
and the Pāli prompt gets the particle, mark and sandhi hints but not the pronoun glosses. In-place hints are cheap for a
model that obeys them and a risk for one that copies them or is thrown by their density (nemotron-120b's nominative braces).
