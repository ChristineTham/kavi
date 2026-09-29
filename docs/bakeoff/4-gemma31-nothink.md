# Bake-off on `dn15-short.md`

2 paragraphs; glossary: default.txt; thinking: off (non-MITRA models)

## As translator

| model | mean s/para | tokens | checker findings left (ask) | checker fixes applied |
| --- | --- | --- | --- | --- |
| mitra-qwen35-translate-mlx-bf16 | 14 | 329 | 2 | 4 |
| gemma-4-31B-it-qat-8bit | 62 | 327 | 0 | 0 |

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

**gemma-4-31B-it-qat-8bit** (92s)

Thus by me was heard—at one time Bhagavā in Kuru dwells, Kammāsadhamma named of Kurus town. Then indeed Āyasmā Ānanda by whom Bhagavā there approached, having approached, having bowed to Bhagavā, to one side sat. To one side seated indeed Āyasmā Ānanda to Bhagavā this said— “Wonderful, Bhante, marvelous, Bhante. As far as profound and this, Bhante, `paṭiccasamuppādo` (dependent origination) profound in appearance and, moreover however to me like very clear it appears.” “Do not thus, Ānanda, say, do not thus, Ānanda, say. Profound and this, Ānanda, `paṭiccasamuppādo` profound in appearance and. Of this, Ānanda, `dhamma` (teaching) by non-comprehension by non-penetration thus this people like a tangled ball of thread, tangled like bird's nest, like muñja grass and reeds, state of loss, state of misery, state of suffering, `saṃsāraṃ` (cycle of rebirth) does not transcend.”


### Paragraph 2

> ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

**mitra-qwen35-translate-mlx-bf16** (6s)

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**gemma-4-31B-it-qat-8bit** (31s)

‘There is because of this `jarāmaraṇa` (old age and death)’ thus with being asked, Ānanda, ‘there is’ thus to him should be said. ‘Because of what `jarāmaraṇa`?’ thus if he would say, ‘because of `jāti` (birth) `jarāmaraṇa`’ thus to him should be said.


## As reviewer (of the first translator's checked draft)

| model | mean s/para | parsed | issues reported | open findings resolved |
| --- | --- | --- | --- | --- |
| gemma-4-31B-it-qat-8bit | 96 | 2/2 | 11 | 2/2 |

### Paragraph 1 — reviewed draft

Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth).”

Open findings handed to the reviewer:
- 'Yāva': particle meaning 'as long as; as far as; so much so; up to; until; from… to' is not rendered — render it (for example 'as long as') where it stands in the sentence
- 'dhammassa': technical term (teaching) not shown in the `word` (gloss) form — write it as `dhamma` (teaching) on its first occurrence, then 'teaching'

**gemma-4-31B-it-qat-8bit** (128s; issues: 6; still open: 0)

- [1] 'Yāva': not rendered; fix: render as "As far as" or "How" (per dictionary/context)
- [1] 'uttānakuttānako viya khāyatī': paraphrased as "as plain as the surface of a pond"; fix: render literally as "appears very clear like"
- [1] 'dhammassa': technical term not in backticks; fix: render as `dhamma` (teaching)
- [1] 'evamayaṃ pajā': "this generation has become" is a paraphrase; fix: render as "thus this people"
- [1] 'tantākulakajātā kulagaṇṭhikajātā muñjapabbajabhūtā': "has become like..." is a paraphrase; fix: render as adjectives "like a tangled ball of thread, tangled like bird's nest, (entwined) like muñja grass and reeds"
- [1] 'apāyaṃ duggatiṃ vinipātaṃ saṃsāraṃ': "the plane of misery, the bad destination, the lower realms" is a paraphrase; fix: render as "the state of loss, the state of misery, the state of suffering, the cycle of rebirth"

Revised: Thus have I heard—at one time the Bhagavā dwells in the Kurus, in a market town of the Kurus named Kammāsadhamma. Then indeed the venerable Ānanda, by whom the Bhagavā [was approached], approached there; having approached, having bowed down to the Bhagavā, he sat to one side. Sitting to one side indeed, the venerable Ānanda said this to the Bhagavā— “Wonderful, Bhante, marvelous, Bhante. As far as deep is this `paṭiccasamuppādo` (dependent origination), Bhante, and deep in appearance it is, then and moreover to me it appears like very clear.” “Do not thus, Ānanda, say, do not thus, Ānanda, say. Deep is this, Ānanda, dependent origination and deep in appearance it is. Of this, Ānanda, `dhamma` (teaching), through non-comprehension, through non-penetration, thus this people, like a tangled ball of thread, tangled like bird's nest, (entwined) like muñja grass and reeds, the state of loss, the state of misery, the state of suffering, the `saṃsāraṃ` (cycle of rebirth) does not transcend.


### Paragraph 2 — reviewed draft

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**gemma-4-31B-it-qat-8bit** (64s; issues: 5; still open: 0)

- [1] ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā: "when asked" is a paraphrase; should be "with being asked" (satā = instrumental present participle)
- [1] ‘Atthi idappaccayā jarāmaraṇan’ti: "Is there a specific condition for..." is a paraphrase; should be "There is, due to this, `jarāmaraṇa` (old age and death)"
- [1] atthītissa: "one should say: 'There is'" is a paraphrase; should be "it should be said: 'there is'" (vacanīyaṃ = potential participle)
- [1] ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya: "If it should be asked" is a paraphrase; should be "if he would say: 'Dependent on what is `jarāmaraṇa`?'" (vadeyya = 3rd person singular "he would say")
- [1] ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ: "With birth as condition, there is old age and death" is a paraphrase; should be "dependent on `jāti` (birth), `jarāmaraṇa`"

Revised: “With being asked thus: ‘There is, due to this, `jarāmaraṇa` (old age and death),’ Ānanda, it should be said thus: ‘there is.’ If he would say thus: ‘Dependent on what is `jarāmaraṇa`?’, to him it should be said thus: ‘dependent on `jāti` (birth), `jarāmaraṇa`.’”
