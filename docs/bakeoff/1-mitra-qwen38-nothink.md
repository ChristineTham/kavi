# Bake-off on `dn15-short.md`

2 paragraphs; glossary: default.txt; thinking: off (non-MITRA models)

## As translator

| model | mean s/para | tokens | checker findings left (ask) | checker fixes applied |
| --- | --- | --- | --- | --- |
| mitra-qwen35-translate-mlx-bf16 | 14 | 329 | 2 | 4 |
| mitra-qwen35-it-mlx-bf16 | 15 | 285 | 2 | 6 |
| Qwen3.8-27B-8bit | 56 | 378 | 1 | 0 |

### Paragraph 1

> Evaṃ me sutaṃ— ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo. Atha kho āyasmā ānando yena bhagavā tenupasaṅkami, upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi. Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca— “acchariyaṃ, bhante, abbhutaṃ, bhante. Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca, atha ca pana me uttānakuttānako viya khāyatī”ti. “Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca. Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa ananubodhā appaṭivedhā evamayaṃ pajā tantākulakajātā kulagaṇṭhikajātā muñjapabbajabhūtā apāyaṃ duggatiṃ vinipātaṃ saṃsāraṃ nātivattati.

**mitra-qwen35-translate-mlx-bf16** (22s)

Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) (*paṭiccasamuppāda*) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth) (*saṃsāra*).”

<details><summary>raw draft and checker</summary>

Thus have I heard: at one time the Blessed One was dwelling among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Blessed One; having approached and paid homage to the Blessed One, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Blessed One: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this dependent origination (*paṭiccasamuppāda*) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the cycle of rebirth (*saṃsāra*).”

- fixed: 'bhagavā': an honorific rendered in English as 'Blessed One' — replaced by 'Bhagavā'
- fixed: 'viharati': present tense (present-tense verb; present 3rd person singular) rendered as past 'was dwelling' — changed to 'dwells'
- open: 'Yāva': particle meaning 'as long as; as far as; so much so; up to; until; from… to' is not rendered — render it (for example 'as long as') where it stands in the sentence
- fixed: 'paṭiccasamuppādo': technical term rendered as plain 'dependent origination' — written as `paṭiccasamuppādo` (dependent origination) on first use
- open: 'dhammassa': technical term (teaching) not shown in the `word` (gloss) form — write it as `dhamma` (teaching) on its first occurrence, then 'teaching'
- fixed: 'saṃsāraṃ': technical term rendered as plain 'cycle of rebirth' — written as `saṃsāraṃ` (cycle of rebirth) on first use

</details>

**mitra-qwen35-it-mlx-bf16** (23s)

Thus I heard: At one time the Bhagavā lives among the Kurus, where there is a town of the Kurus called Kammāsadhamma. Then the venerable Ānanda approached the Bhagavā, and after approaching and worshipping the Bhagavā, he sat down at one side. While sitting at one side, the venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante, it is marvellous, Bhante, how deep this `paṭiccasamuppādo` (dependent origination) is, and how deep it appears, yet to me it seems as clear as clear can be.” “Do not say that, Ānanda, do not say that. This dependent origination is deep and it appears deep. Because of not understanding, because of not penetrating this `dhamma` (teaching), Ānanda, this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds, and does not pass beyond the plane of misery, the bad destination, the lower realm, the `saṃsāraṃ` (cycle of rebirth).

<details><summary>raw draft and checker</summary>

Thus I heard: At one time the Sublime One was living among the Kurus, where there is a town of the Kurus called Kammāsadhamma. Then the venerable Ānanda approached the Sublime One, and after approaching and worshipping the Sublime One, he sat down at one side. While sitting at one side, the venerable Ānanda said this to the Sublime One: “It is wonderful, venerable sir, it is marvellous, venerable sir, how deep this dependent origination is, and how deep it appears, yet to me it seems as clear as clear can be.” “Do not say that, Ānanda, do not say that. This dependent origination is deep and it appears deep. Because of not understanding, because of not penetrating this teaching, Ānanda, this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds, and does not pass beyond the plane of misery, the bad destination, the lower realm, the cycle of rebirth.

- fixed: 'bhagavā': an honorific rendered in English as 'Sublime One' — replaced by 'Bhagavā'
- fixed: 'viharati': present tense (present-tense verb; present 3rd person singular) rendered as past 'was living' — changed to 'lives'
- fixed: 'bhante': an honorific rendered in English as 'venerable sir' — replaced by 'Bhante'
- open: 'Yāva': particle meaning 'as long as; as far as; so much so; up to; until; from… to' is not rendered — render it (for example 'as long as') where it stands in the sentence
- fixed: 'paṭiccasamuppādo': technical term rendered as plain 'dependent origination' — written as `paṭiccasamuppādo` (dependent origination) on first use
- fixed: 'dhammassa': technical term rendered as plain 'teaching' — written as `dhamma` (teaching) on first use
- fixed: 'saṃsāraṃ': technical term rendered as plain 'cycle of rebirth' — written as `saṃsāraṃ` (cycle of rebirth) on first use

</details>

**Qwen3.8-27B-8bit** (84s)

Thus I have heard— on one occasion the Bhagavā dwells in the Kurus at Kammāsadhamma, a town of the Kurus. Then indeed the venerable Ānanda went to the Bhagavā, and having approached, having bowed down to the Bhagavā, sat down at one side. Having sat down at one side, the venerable Ānanda said this to the Bhagavā— “Wonderful, Bhante, extraordinary, Bhante. As far as this `paṭiccasamuppādo` (dependent origination) is profound and its appearance is profound, yet it seems to me as if it were plainly obvious.” “Do not say so, Ānanda, do not say so. This dependent origination is indeed profound and its appearance is profound. For this `dhamma` (teaching), Ānanda, through non-comprehension and non-penetration, this people is born like a tangled ball of thread, born like a bird’s nest, become like muñja grass and reeds; they do not transcend the state of loss, the bad destination, the lower realm, the `saṃsāra` (cycle of rebirth).

<details><summary>raw draft and checker</summary>

Thus I have heard— on one occasion the Bhagavā dwells in the Kurus at Kammāsadhamma, a town of the Kurus. Then indeed the venerable Ānanda went to the Bhagavā, and having approached, having bowed down to the Bhagavā, sat down at one side. Having sat down at one side, the venerable Ānanda said this to the Bhagavā— “Wonderful, Bhante, extraordinary, Bhante. As far as this `paṭiccasamuppādo` (dependent origination) is profound and its appearance is profound, yet it seems to me as if it were plainly obvious.” “Do not say so, Ānanda, do not say so. This `paṭiccasamuppādo` (dependent origination) is indeed profound and its appearance is profound. For this `dhamma` (teaching), Ānanda, through non-comprehension and non-penetration, this people is born like a tangled ball of thread, born like a bird’s nest, become like muñja grass and reeds; they do not transcend the state of loss, the bad destination, the lower realm, the `saṃsāra` (cycle of rebirth).

- open: 'nātivattati': present tense (present-tense verb (from na ativattati); present 3rd person singular) may have been rendered as past — use the present: 'does not overstep'

</details>


### Paragraph 2

> ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

**mitra-qwen35-translate-mlx-bf16** (7s)

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**mitra-qwen35-it-mlx-bf16** (7s)

‘There is this condition for old age and death,’ Ānanda, being asked thus, you should say ‘There is.’ ‘What is the condition for old age and death?’ being asked thus, you should say ‘Birth is the condition for old age and death.’

- open: 'ce': particle meaning 'if' is not rendered — render it (for example 'if') where it stands in the sentence

**Qwen3.8-27B-8bit** (29s)

“Is there `jarāmaraṇa` (old age and death) due to this?” thus asked, Ānanda, should be said to him who exists. If he would say, “Due to what condition is old age and death?” thus to him should be said, “Due to `jāti` (birth) is old age and death.”

<details><summary>raw draft and checker</summary>

“Is there `jarāmaraṇa` (old age and death) due to this?” thus asked, Ānanda, should be said to him who exists. If he would say, “Due to what condition is `jarāmaraṇa` (old age and death)?” thus to him should be said, “Due to `jāti` (birth) is `jarāmaraṇa` (old age and death).”



</details>


## As reviewer (of the first translator's checked draft)

| model | mean s/para | parsed | issues reported | open findings resolved |
| --- | --- | --- | --- | --- |
| mitra-qwen35-it-mlx-bf16 | 23 | 2/2 | 4 | 2/2 |
| Qwen3.8-27B-8bit | 133 | 2/2 | 24 | 2/2 |

### Paragraph 1 — reviewed draft

Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) (*paṭiccasamuppāda*) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth) (*saṃsāra*).”

Open findings handed to the reviewer:
- 'Yāva': particle meaning 'as long as; as far as; so much so; up to; until; from… to' is not rendered — render it (for example 'as long as') where it stands in the sentence
- 'dhammassa': technical term (teaching) not shown in the `word` (gloss) form — write it as `dhamma` (teaching) on its first occurrence, then 'teaching'

**mitra-qwen35-it-mlx-bf16** (32s; issues: 2; still open: 0)

- Segment [1]: 'Yāva' is not translated; it should be rendered as 'as long as'
- Segment [1]: 'dhammassa' is not rendered in the technical term gloss form; it should be written as `dhamma` (teaching) on its first occurrence

Revised: Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! As long as this `paṭiccasamuppādo` (dependent origination) (*paṭiccasamuppāda*) is deep, Bhante, and as deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this `dhamma` (teaching) (*dhamma*), Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth) (*saṃsāra*).”

**Qwen3.8-27B-8bit** (132s; issues: 4; still open: 0)

- Segment [1], 'Yāva': The particle is missing from the translation. It must be rendered (e.g., "as long as" or "how") to reflect the Pāli structure.
- Segment [1], 'dhammassa': The technical term `dhamma` is not formatted with backticks and a gloss on its first occurrence. It should be `dhamma` (teaching).
- Segment [1], 'khāyatī': The translation "as plain as the surface of a pond" is an interpretive paraphrase not supported by the literal meaning of *khāyatī* (which relates to *kha* space/sky or *yati* striving/monks, often interpreted in commentaries as "like the sky" or "clear"). However, given the strict rule against interpretation and the dictionary entry for *khā* (space/sky) and *yatī* (strived/monk), a more literal rendering is required. The standard translation for this specific idiom (*uttānakuttānako viya khāyatī*) is often "like the sky" or "clear like the sky". The current translation adds "surface of a pond" which is not in the text. I will correct it to "clear like the sky" based on *kha* (sky/space) being the primary component of the compound in this context, or simply "clear" if *khāyatī* is treated as an adjective. Let's look at the dictionary: *khā* (space/sky) + *yatī* (strived/monk). Actually, *khāyatī* is often analyzed as *kha* (sky) + *yati* (goes/strives) or simply an adjective meaning "clear". The phrase *uttānakuttānako viya khāyatī* is a fixed expression. A literal translation of *khāyatī* based on *kha* (sky) is "like the sky". The previous translation "surface of a pond" is an error. I will use "clear like the sky".
- Segment [1], 'saṃsāraṃ': The technical term `saṃsāra` is not formatted with backticks and a gloss on its first occurrence. It should be `saṃsāra` (cycle of rebirth).

Revised: Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! As long as this `paṭiccasamuppādo` (dependent origination) is deep, Bhante, and appears deep, yet to me it seems clear like the sky.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this `dhamma` (teaching), Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the state of loss, the bad destination, the lower realms, and the `saṃsāra` (cycle of rebirth).”


### Paragraph 2 — reviewed draft

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**mitra-qwen35-it-mlx-bf16** (13s; issues: 2; still open: 0)

- Segment [1]: The translation of ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ’ is slightly awkward and could be made more literal.
- Segment [1]: The phrase ‘one should say to him’ is an interpretation rather than a literal rendering of the Pāli structure.

Revised: “Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**Qwen3.8-27B-8bit** (134s; issues: 20; still open: 0)

- Segment 1, "Atthi idappaccayā jarāmaraṇan’ti": The translation "Is there a specific condition for old age and death?" is inaccurate. "Atthi" means "there is", "idappaccayā" means "due to this" or "with this as condition". The Pāli phrase is a statement of existence/conditionality, not a question about the *existence* of a condition. The standard rendering for this formula is "There is old age and death due to this" or "With this as condition, there is old age and death". The translation incorrectly frames it as a question about whether a condition exists, rather than stating the conditional relationship.
- Segment 1, "puṭṭhena satā": The translation "when asked" is acceptable, but the structure "one should say: 'There is.'" for "atthītissa vacanīyaṃ" is slightly off. "Atthi" in the answer refers to the existence of the phenomenon (old age and death) under the condition, or simply affirming the premise. However, looking at the second part "Kiṃpaccayā... jātipaccayā...", the first part is likely establishing the fact that old age and death *is* conditioned. The translation "Is there a specific condition..." misses the nuance of "idappaccayā" (due to *this*). A more literal and faithful translation of the first quote is "With this as condition, there is old age and death." The answer "There is" (Atthi) confirms the existence of the conditioned phenomenon.
- Segment 1, "Kiṃpaccayā jarāmaraṇan’ti": The translation "With what as condition is there old age and death?" is good.
- Segment 1, "jātipaccayā jarāmaraṇan’ti": The translation "With birth as condition, there is old age and death." is good.
- Segment 1, "iccassa": The translation "to him" is correct for the dative pronoun.
- Let's refine the first part.
- Pāli: 'Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā...
- Literal: When asked "There is old age and death due to this" (or "With this as condition, there is old age and death")...
- The translation "Is there a specific condition for old age and death?" changes the meaning. The Pāli is quoting a statement: "Atthi idappaccayā jarāmaraṇan'ti". This is a declarative sentence in the quote. The question mark in the English translation is wrong because the Pāli quote ends with `iti` (thus) and is a statement. The *act* of asking is described by `puṭṭhena satā` (when asked). The content of the question is the statement "Atthi idappaccayā jarāmaraṇan'ti". Wait, usually in these dialogues, the question is "Kiṃpaccayā..." (What is the condition?). But here the first quote is "Atthi idappaccayā jarāmaraṇan'ti". This looks like the *answer* to a previous question or a statement being affirmed.
- Actually, looking at the context of dependent origination texts (e.g., SN 12.1), the pattern is often:
- Q: "Kiṃpaccayā jarāmaraṇan'ti?" (What is the condition for old age and death?)
- A: "Jātipaccayā jarāmaraṇan'ti." (With birth as condition, there is old age and death.)
- However, the Pāli provided in Segment 1 starts with: `'Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā`.
- This translates to: "When asked 'There is old age and death due to this'..."
- This implies the questioner is asking for confirmation or elaboration on the statement "There is old age and death due to this".
- The answer given is `atthītissa vacanīyaṃ` -> "It should be said: 'There is.'" (or "Yes, there is").
- Then the second part: `'Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya` -> "If it should be said/asked: 'With what as condition is there old age and death?'"
- Answer: `'jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ` -> "It should be said to him: 'With birth as condition, there is old age and death.'"
- The current translation renders the first quote as a question: "Is there a specific condition for old age and death?". This is incorrect. The Pāli quote is `Atthi idappaccayā jarāmaraṇan’ti`. This is a statement: "There is old age and death due to this." The word `puṭṭhena satā` means "when asked [this]". So the English should be: "When asked, 'There is old age and death due to this,' one should say, 'There is.'"
- Also, `idappaccayā` means "due to this" or "with this as condition". The translation "specific condition" is an interpretation, not a literal rendering of `idappaccayā`.

Revised: “Ānanda, when asked, ‘There is old age and death due to this,’ one should say, ‘There is.’ If it should be asked, ‘With what as condition is there old age and death?’ one should say to him, ‘With birth as condition, there is old age and death.’”
