# Stage 1 on the Prajñāpāramitāstotra: the prompt loop of 2026-11-13

`gemma4:26b-mlx` through Ollama (the default model at the time) made the Stage 1 discourse draft of Rāhulabhadra's hymn (21 verses,
42 lines, one model call of about 20 seconds) six times; each draft was judged line by line against
`Prajñāpāramitāstotra-ref.md` and the conventions, and the prompt was revised between rounds. Drafts 5 and 6 used the
same prompt. `Prajñāpāramitāstotra-gemma-26b.md` is the draft made afterwards with the frozen prompt (chrF 60.4,
word F1 67.6), the baseline of the comparison of models that followed.

| draft | lines right / 42 | sense errors | convention only | vocative epithets in form / 8 | chrF | word F1 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 13 | 23 | 6 | 0 | 58.5 | 65.3 |
| 2 | 5 | 23 | 14 | 0 | 56.6 | 65.4 |
| 3 | 6 | 23 | 13 | 2 | 58.3 | 63.7 |
| 4 | 14 | 22 | 6 | 7 | 58.8 | 66.4 |
| 5 | 13 | 27 | 2 | 8 | 59.4 | 66.7 |
| 6 | 11 | 28 | 3 | 8 | 59.3 | 67.2 |

(One reviewer regraded all six drafts by one standard for this table.)

## What the loop showed

- **The prompt moves conventions, not sense.** The epithet form went from 0 of 8 to 8 of 8 and the convention-only
  lines from 6 to 2; the sense errors stayed between 22 and 28 throughout.
- **Nineteen lines are wrong in every draft**, whatever the prompt said: vocabulary the model does not have
  (*puraḥsarī* an "ocean", *pitāmahī* "grandfather", *candralekhā* "moon-rays", *nirnimitta* "unmotivated",
  *nirvikalpa* five different wrong glosses), agreement across the half-verse, an accusative made the subject
  (*tvām eva badhyate paśyan*, also with the rule stated), the locative absolute and the desiderative of the last verses.
  These are Stage 2's to correct from the dictionary.
- **Five to seven lines are right in nearly every draft**: short lines of plain syntax and common words.
- **The same prompt gives different drafts** at temperature 0: 23 of 42 lines differed in wording between drafts 5 and
  6, two in verdict. A difference of about two lines between rounds is not a signal.
- **A list is obeyed; a description is not.** Every list the pipeline generated from the lexicon (names and titles to
  keep bare, forms that can be words of address) was followed; sentences describing a class ("an adverb of manner",
  "a word that describes the one addressed", "keep the gender") were ignored or over-applied.
- **What a change can cost**: blank lines between verses made the model copy the source's `//`; "every word of
  address is written one of two ways" made it backtick sixty words; a gender sentence with the example "mother" turned
  two other nouns into "mother".

## What changed in kavi

In the Stage 1 prompt (`Translator._contextual_macro_pass`): the glossary's renderings for the terms of the chunk; a
closed list of the names and titles of the chunk as they are to be written; the forms that can be words of address,
with the rule that only these may take the `word` (English) form; verses set apart by a blank line and a short
construing rule; the title's English once; an apostrophe as an elided a-. In code rather than in words: line-end marks
(`/`, `//`, `|`, `||`) are taken off the source lines, a number given twice keeps its first line, a verse begins with
a capital, a parenthesis after a listed name is removed. `kavi translate --stage1` gives the draft alone.

Tried and taken out again: a generated list of the glossary words standing alone in the instrumental or ablative (no
effect) and a sentence on gender (no effect, then harm). The sentence that asks for the word's case to be looked at
before a glossary rendering is used stayed in the prompt (it did nothing either).
