# Bake-off on `dn15-short.md`

2 paragraphs; glossary: default.txt; thinking: off (non-MITRA models)

## As translator

| model | mean s/para | tokens | checker findings left (ask) | checker fixes applied |
| --- | --- | --- | --- | --- |
| mitra-qwen35-translate-mlx-bf16 | 14 | 329 | 2 | 4 |
| gemma-4-26B-A4B-it-qat-8bit | 11 | 362 | 2 | 0 |

### Paragraph 1

> Evaṃ me sutaṃ— ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo. Atha kho āyasmā ānando yena bhagavā tenupasaṅkami, upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi. Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca— “acchariyaṃ, bhante, abbhutaṃ, bhante. Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca, atha ca pana me uttānakuttānako viya khāyatī”ti. “Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca. Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa ananubodhā appaṭivedhā evamayaṃ pajā tantākulakajātā kulagaṇṭhikajātā muñjapabbajabhūtā apāyaṃ duggatiṃ vinipātaṃ saṃsāraṃ nātivattati.

**mitra-qwen35-translate-mlx-bf16** (22s)

Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth).”

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

**gemma-4-26B-A4B-it-qat-8bit** (16s)

Thus me heard—a certain time Bhagavā in Kurūsu dwells, Kammāsadhamma named, a nigama (market town) of Kurū. Then indeed Āyasmā Ānanda by which Bhagavā that place approached, having approached Bhagavanta having bowed down, to one side sat. Seated to one side indeed Āyasmā Ānanda Bhagavanta this said— “Wonderful!, Bhante, marvellous!, Bhante. As long as deep also this, Bhante, `paṭiccasamuppādo` (dependent origination) and deep in appearance also, but moreover to me like a stretched-up-and-stretched-down-one (very clear) it eats.” “Do not indeed thus, Ānanda, speak, do not indeed thus, Ānanda, speak. Deep also this, Ānanda, dependent origination and deep in appearance also. For this `dhammassa` (teaching) non-comprehension and non-penetration, thus this progeny like a tangled ball of thread, like a bird's nest, like entwined muñja grass and reeds, the state of loss, the bad destination, the underworld, `saṃsāraṃ` (cycle of rebirth) does not exceed.”

<details><summary>raw draft and checker</summary>

Thus me heard—a certain time Bhagavā in Kurūsu dwells, Kammāsadhamma named, a nigama (market town) of Kurū. Then indeed Āyasmā Ānanda by which Bhagavā that place approached, having approached Bhagavanta having bowed down, to one side sat. Seated to one side indeed Āyasmā Ānanda Bhagavanta this said— “Wonderful!, Bhante, marvellous!, Bhante. As long as deep also this, Bhante, `paṭiccasamuppādo` (dependent origination) and deep in appearance also, but moreover to me like a stretched-up-and-stretched-down-one (very clear) it eats.” “Do not indeed thus, Ānanda, speak, do not indeed thus, Ānanda, speak. Deep also this, Ānanda, `paṭiccasamuppādo` (dependent origination) and deep in appearance also. For this `dhammassa` (teaching) non-comprehension and non-penetration, thus this progeny like a tangled ball of thread, like a bird's nest, like entwined muñja grass and reeds, the state of loss, the bad destination, the underworld, `saṃsāraṃ` (cycle of rebirth) does not exceed.”

- open: 'kurūsu': a name (name of a country) does not appear untranslated — put 'Kuru' in place of whatever English stands for it
- open: 'kurūnaṃ': a name (name of a country) does not appear untranslated — put 'Kuru' in place of whatever English stands for it

</details>


### Paragraph 2

> ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

**mitra-qwen35-translate-mlx-bf16** (7s)

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**gemma-4-26B-A4B-it-qat-8bit** (5s)

‘Due to this condition there is `jarāmaraṇaṃ` (old age and death)’ thus, Ānanda, by being asked by a seeker, should be said. ‘If he would say, ‘Due to what condition `jarāmaraṇaṃ`?’ then thus to him should be said, ‘Due to the condition of `jāti` (birth) there is `jarāmaraṇaṃ`’.


## As reviewer (of the first translator's checked draft)

| model | mean s/para | parsed | issues reported | open findings resolved |
| --- | --- | --- | --- | --- |
| gemma-4-26B-A4B-it-qat-8bit | 13 | 2/2 | 5 | -1/2 |

### Paragraph 1 — reviewed draft

Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth).”

Open findings handed to the reviewer:
- 'Yāva': particle meaning 'as long as; as far as; so much so; up to; until; from… to' is not rendered — render it (for example 'as long as') where it stands in the sentence
- 'dhammassa': technical term (teaching) not shown in the `word` (gloss) form — write it as `dhamma` (teaching) on its first occurrence, then 'teaching'

**gemma-4-26B-A4B-it-qat-8bit** (18s; issues: 4; still open: 3)

- [1] Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca: 'Yāva' is not rendered; add 'As long as'
- [1] dhammassa: technical term not in backticks; change to `dhammassa` (teaching)
- [1] khāyatī viya: 'as plain as the surface of a pond' is an interpretation/addition; render literally as 'strives in space like' or similar based on the dictionary (khā: space; yatī: strives/exerts oneself)
- [1] saṃsāraṃ: technical term not in backticks; change to `saṃsāraṃ` (cycle of rebirth)

Revised: Thus have I heard: at one a certain time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then indeed the Venerable Ānanda approached where the Bhagavā was, having approached and having paid high respect to the Bhagavā, he sat down to one side. Sitting to one side indeed the Venerable Ānanda said this to the Bhagavā— “Wonderful!, Bhante, marvelous!, Bhante. As long as deep is this and `paṭiccasamuppādo` (dependent origination) [is] deep in appearance, moreover to me it strives like three [things] in space.”


### Paragraph 2 — reviewed draft

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**gemma-4-26B-A4B-it-qat-8bit** (8s; issues: 1; still open: 0)

- [1] ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā: The translation "when asked" is a paraphrase of the instrumental "by being asked"; the translation "Is there a specific condition for..." is an interpretation/paraphrase of "There is due to this [condition] old age and death"; the translation "one should say: 'There is'" is a misinterpretation of the grammar (the text says "it is to be said thus: 'There is due to this [condition] old age and death' by being asked"); the translation "If it should be asked" is a paraphrase of "If he would say"; the translation "one should say to him" is a paraphrase of "it is to be said to him".

Revised: “By being asked, ‘There is due to this `jarāmaraṇaṃ` (old age and death),’ thus, Ānanda, it is to be said: ‘There is due to this.’ If he would say, ‘Due to what condition is there old age and death?’, it is to be said to him: ‘Due to birth, there is old age and death.’”
