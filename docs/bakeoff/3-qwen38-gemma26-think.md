# Bake-off on `dn15-short.md`

2 paragraphs; glossary: default.txt; thinking: on (non-MITRA models)

## As translator

| model | mean s/para | tokens | checker findings left (ask) | checker fixes applied |
| --- | --- | --- | --- | --- |
| mitra-qwen35-translate-mlx-bf16 | 14 | 329 | 2 | 4 |
| Qwen3.8-27B-8bit | 214 | 4096 | 0 | 0 |
| gemma-4-26B-A4B-it-qat-8bit | 43 | 4096 | 2 | 1 |

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

**Qwen3.8-27B-8bit** (235s)

We need answer user's request: translate Pali into English literally and faithfully, word by word as far as English allows, render every word in grammatical form given, keep Pali word order where English allows, add nothing. Answer with translation only. Need use dictionary analysis. Need likely produce a literal translation of the passage (SN 12.2? Kammāsadhamma Sutta). Need obey rules: render every word, drop no particle. Leave personal names, place names, titles of texts untranslated in stem form: Kammāsadhamma, Kuru, Ānanda. Leave honorifics and titles of persons untranslated exactly as they stand: Bhagavā, Bhante. Technical terms keep as in text in backticks with short English gloss on first occurrence: candidates include dhamma (teaching), paṭiccasamuppādo (dependent origination), saṃsāraṃ (cycle of rebirth). Need maybe also `paṭiccasamuppādo` first occurrence, `dhammassa`? The rule says where a word is used as technical term, keep it as it stands in text in backticks with short English gloss on first occurrence. Candidates in this text: `dhamma` (teaching), `paṭiccasamuppādo` (dependent origination), `saṃsāraṃ` (cycle of rebirth). In text: paṭiccasamuppādo appears twice? First in Ananda's quote: "Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca". Then Buddha: "Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa..." So first occurrence of paṭiccasamuppādo should be backticked with gloss. dhammassa is genitive of dhamma; technical term? It says teaching. But word in text is dhammassa, not dhamma. Rule: keep it as it stands in the text in backticks with gloss on first occurrence, like `viññāṇaṃ` (consciousness). So if technical term dhamma used as teaching, first occurrence in text is dhammassa. Should we backtick `dhammassa` (teaching)? The candidate list says teaching, but text has dhammassa. It says keep it as it stands in the text. So likely teaching on first occurrence? But dhammassa is genitive singular "of this teaching". Could backtick teaching maybe awkward. Or since candidate is dhamma, but not exact? Need decide. Also saṃsāraṃ appears at end; backtick cycle of rebirth. Need maybe not backtick paṭiccasamuppādo second time? Use plain gloss afterwards: dependent origination. But if first occurrence backticked, second can be plain "dependent origination"? The rule: keep it as it stands in text in backticks with short English gloss on first occurrence, and use plain gloss afterwards. So second occurrence: dependent origination (no backticks). But if we keep Pali word order, maybe "this dependent origination is deep and deep in appearance". Need literal.

Need translate every word. Let's parse passage:
Evaṃ me sutaṃ— ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo. Atha kho āyasmā ānando yena bhagavā tenupasaṅkami, upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi. Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca— “acchariyaṃ, bhante, abbhutaṃ, bhante. Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca, atha ca pana me uttānakuttānako viya khāyatī”ti. “Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca. Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa ananubodhā appaṭivedhā evamayaṃ pajā tantākulakajātā kulagaṇṭhikajātā muñjapabbajabhūtā apāyaṃ duggatiṃ vinipātaṃ saṃsāraṃ nātivattati.

Need literal word-by-word as far as English allows, keep Pali order where English allows. Need render every particle: ca, pana, kho, atha, eva? hevaṃ? etc.

Let's make a literal translation preserving order:
"Thus to me heard— at one time Bhagavā in Kurus dwells Kammāsadhamma named of Kurus town. Then indeed venerable Ānanda to where Bhagavā there approached, having approached Bhagavā having bowed down to one side sat. To one side seated indeed venerable Ānanda Bhagavā this said— 'Wonderful, Bhante, marvellous, Bhante. As far as deep this, Bhante, dependent origination deep in appearance and, but and indeed to me very clear like is consumed/ends?' 'Do not thus, Ānanda, say, do not thus, Ānanda, say. Deep this, Ānanda, dependent origination deep in appearance and. Of this, Ānanda, teaching non-comprehension non-penetration thus this people like a tangled ball of thread tangled like bird's nest entwined like muñja grass and reeds state of loss state of misery lower realm cycle of rebirth does not overstep."

Need refine to be grammatical enough but literal. Need render every word: "Evaṃ me sutaṃ" = Thus to me heard. Could be "Thus I have heard" but literal: "Thus to me heard". Need maybe "Thus by me heard"? Dictionary me can be dative/accusative/instrumental. In standard formula "Thus have I heard" but literal maybe "Thus to me heard". The instruction: render every word in grammatical form dictionary gives. me could be dative "to me" or accusative "me". sutaṃ neuter nom/acc "heard". So "Thus to me heard" okay.

"ekaṃ samayaṃ" = at one time / a certain time. "bhagavā kurūsu viharati" = Bhagavā in Kurus dwells. "kammāsadhammaṃ nāma kurūnaṃ nigamo" = Kammāsadhamma named of Kurus town. Need word order: "Kammāsadhamma named of Kurus town" maybe "Kammāsadhamma, named, of Kurus town". nāma = called/named. kurūnaṃ = of Kurus (genitive plural). nigamo = town (nom singular). So "Kammāsadhamma named of Kurus town". Could be "the town of the Kurus named Kammāsadhamma" but word order Pali: kammāsadhammaṃ nāma kurūnaṃ nigamo. Keep as far as English allows: "Kammāsadhamma named of Kurus town". Maybe "Kammāsadhamma, named, the town of the Kurus." But "of Kurus" literal. Need not add article? "a town"? ekaṃ? no.

"Atha kho āyasmā ānando yena bhagavā tenupasaṅkami" = Then indeed venerable Ānanda to where Bhagavā there approached. yena = to/towards (instrumental? adverb). tenupasaṅkami = approached there. Could be "to where Bhagavā was, there he approached". But literal: "Then indeed venerable Ānanda to where Bhagavā there approached". Need maybe "to the place of Bhagavā he approached there"? But yena bhagavā = to where Bhagavā (is). tenupasaṅkami = approached there. So "Then

<details><summary>raw draft and checker</summary>

We need answer user's request: translate Pali into English literally and faithfully, word by word as far as English allows, render every word in grammatical form given, keep Pali word order where English allows, add nothing. Answer with translation only. Need use dictionary analysis. Need likely produce a literal translation of the passage (SN 12.2? Kammāsadhamma Sutta). Need obey rules: render every word, drop no particle. Leave personal names, place names, titles of texts untranslated in stem form: Kammāsadhamma, Kuru, Ānanda. Leave honorifics and titles of persons untranslated exactly as they stand: Bhagavā, Bhante. Technical terms keep as in text in backticks with short English gloss on first occurrence: candidates include dhamma (teaching), paṭiccasamuppādo (dependent origination), saṃsāraṃ (cycle of rebirth). Need maybe also `paṭiccasamuppādo` first occurrence, `dhammassa`? The rule says where a word is used as technical term, keep it as it stands in text in backticks with short English gloss on first occurrence. Candidates in this text: `dhamma` (teaching), `paṭiccasamuppādo` (dependent origination), `saṃsāraṃ` (cycle of rebirth). In text: paṭiccasamuppādo appears twice? First in Ananda's quote: "Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca". Then Buddha: "Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa..." So first occurrence of paṭiccasamuppādo should be backticked with gloss. dhammassa is genitive of dhamma; technical term? It says `dhamma` (teaching). But word in text is dhammassa, not dhamma. Rule: keep it as it stands in the text in backticks with gloss on first occurrence, like `viññāṇaṃ` (consciousness). So if technical term dhamma used as teaching, first occurrence in text is dhammassa. Should we backtick `dhammassa` (teaching)? The candidate list says `dhamma` (teaching), but text has dhammassa. It says keep it as it stands in the text. So likely `dhammassa` (teaching) on first occurrence? But dhammassa is genitive singular "of this teaching". Could backtick `dhammassa` (teaching) maybe awkward. Or since candidate is dhamma, but not exact? Need decide. Also saṃsāraṃ appears at end; backtick `saṃsāraṃ` (cycle of rebirth). Need maybe not backtick paṭiccasamuppādo second time? Use plain gloss afterwards: dependent origination. But if first occurrence backticked, second can be plain "dependent origination"? The rule: keep it as it stands in text in backticks with short English gloss on first occurrence, and use plain gloss afterwards. So second occurrence: dependent origination (no backticks). But if we keep Pali word order, maybe "this dependent origination is deep and deep in appearance". Need literal.

Need translate every word. Let's parse passage:
Evaṃ me sutaṃ— ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo. Atha kho āyasmā ānando yena bhagavā tenupasaṅkami, upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi. Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca— “acchariyaṃ, bhante, abbhutaṃ, bhante. Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca, atha ca pana me uttānakuttānako viya khāyatī”ti. “Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca. Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa ananubodhā appaṭivedhā evamayaṃ pajā tantākulakajātā kulagaṇṭhikajātā muñjapabbajabhūtā apāyaṃ duggatiṃ vinipātaṃ saṃsāraṃ nātivattati.

Need literal word-by-word as far as English allows, keep Pali order where English allows. Need render every particle: ca, pana, kho, atha, eva? hevaṃ? etc.

Let's make a literal translation preserving order:
"Thus to me heard— at one time Bhagavā in Kurus dwells Kammāsadhamma named of Kurus town. Then indeed venerable Ānanda to where Bhagavā there approached, having approached Bhagavā having bowed down to one side sat. To one side seated indeed venerable Ānanda Bhagavā this said— 'Wonderful, Bhante, marvellous, Bhante. As far as deep this, Bhante, `paṭiccasamuppādo` (dependent origination) deep in appearance and, but and indeed to me very clear like is consumed/ends?' 'Do not thus, Ānanda, say, do not thus, Ānanda, say. Deep this, Ānanda, dependent origination deep in appearance and. Of this, Ānanda, `dhammassa` (teaching) non-comprehension non-penetration thus this people like a tangled ball of thread tangled like bird's nest entwined like muñja grass and reeds state of loss state of misery lower realm `saṃsāraṃ` (cycle of rebirth) does not overstep."

Need refine to be grammatical enough but literal. Need render every word: "Evaṃ me sutaṃ" = Thus to me heard. Could be "Thus I have heard" but literal: "Thus to me heard". Need maybe "Thus by me heard"? Dictionary me can be dative/accusative/instrumental. In standard formula "Thus have I heard" but literal maybe "Thus to me heard". The instruction: render every word in grammatical form dictionary gives. me could be dative "to me" or accusative "me". sutaṃ neuter nom/acc "heard". So "Thus to me heard" okay.

"ekaṃ samayaṃ" = at one time / a certain time. "bhagavā kurūsu viharati" = Bhagavā in Kurus dwells. "kammāsadhammaṃ nāma kurūnaṃ nigamo" = Kammāsadhamma named of Kurus town. Need word order: "Kammāsadhamma named of Kurus town" maybe "Kammāsadhamma, named, of Kurus town". nāma = called/named. kurūnaṃ = of Kurus (genitive plural). nigamo = town (nom singular). So "Kammāsadhamma named of Kurus town". Could be "the town of the Kurus named Kammāsadhamma" but word order Pali: kammāsadhammaṃ nāma kurūnaṃ nigamo. Keep as far as English allows: "Kammāsadhamma named of Kurus town". Maybe "Kammāsadhamma, named, the town of the Kurus." But "of Kurus" literal. Need not add article? "a town"? ekaṃ? no.

"Atha kho āyasmā ānando yena bhagavā tenupasaṅkami" = Then indeed venerable Ānanda to where Bhagavā there approached. yena = to/towards (instrumental? adverb). tenupasaṅkami = approached there. Could be "to where Bhagavā was, there he approached". But literal: "Then indeed venerable Ānanda to where Bhagavā there approached". Need maybe "to the place of Bhagavā he approached there"? But yena bhagavā = to where Bhagavā (is). tenupasaṅkami = approached there. So "Then



</details>

**gemma-4-26B-A4B-it-qat-8bit** (47s)

<|channel>thought
*   Source: Pāli text.
    *   Target: English translation.
    *   Constraints:
        *   Literal and faithful, word by word as far as English allows.
        *   Render every word in the grammatical form given by dictionary analysis (case, number, tense, person, voice).
        *   Keep Pāli word order where English allows.
        *   Add nothing (no explanation, no commentary, no interpretation, no assumption of religion).
        *   Leave personal names, place names, and titles untranslated in stem form (Kammāsadhamma, Kuru, Ānanda).
        *   Leave honorifics/titles untranslated (Bhagavā, Bhante).
        *   Technical terms: Keep in backticks with a short English gloss on first occurrence (e.g., `paṭiccasamuppādo` (dependent origination)).
        *   Answer with the translation only.

    *   *Evaṃ me sutaṃ—*
        *   Evaṃ: thus
        *   me: by me (instrumental) / to me (dative) / me (accusative). In "Evaṃ me sutaṃ", it's usually "Thus by me [it was] heard".
        *   sutaṃ: heard (past participle, neuter nominative singular).
        *   Translation: Thus by me [it was] heard—

    *   *ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo.*
        *   ekaṃ: a
        *   samayaṃ: time (masculine accusative singular)
        *   bhagavā: Bhagavā (nominative singular)
        *   kurūsu: in Kuru (masculine locative plural)
        *   viharati: dwells (present 3rd person singular)
        *   kammāsadhammaṃ: Kammāsadhamma (neuter nominative singular)
        *   nāma: named
        *   kurūnaṃ: of Kuru (masculine genitive plural)
        *   nigamo: town (masculine nominative singular)
        *   Translation: a time Bhagavā dwells in Kuru, Kammāsadhamma named [is the] town of Kuru.
        *   Refining word order: a time Bhagavā dwells in Kuru, Kammāsadhamma named [is the] town of Kuru. (Wait, "nigamo" is the subject/complement).
        *   Let's look at the structure: "ekaṃ samayaṃ bhagavā kurūsu viharati [at] kammāsadhammaṃ nāma kurūnaṃ nigamo."
        *   Literal: a time Bhagavā in Kuru dwells, Kammāsadhamma named [is the] town of Kuru.

    *   *Atha kho āyasmā ānando yena bhagavā tenupasaṅkami,*
        *   Atha: Then
        *   kho: indeed
        *   āyasmā: Āyasmā (nominative singular)
        *   ānando: Ānanda (nominative singular)
        *   yena: by which / where
        *   bhagavā: Bhagavā (nominative singular)
        *   tenupasaṅkami: approached there (aorist 3rd person singular)
        *   Translation: Then indeed Āyasmā Ānanda, where Bhagavā [was], approached there,

    *   *upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi.*
        *   upasaṅkamitvā: having approached (absolutive)
        *   bhagavantaṃ: Bhagavanta (accusative singular)
        *   abhivādetvā: having bowed down (absolutive)
        *   ekamantaṃ: to one side (adverb)
        *   nisīdi: sat down (aorist 3rd person singular)
        *   Translation: having approached, having bowed down to Bhagavanta, [he] sat down to one side.

    *   *Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca—*
        *   Ekamantaṃ: To one side (adverb)
        *   nisinno: seated (past participle, masculine nominative singular)
        *   kho: indeed
        *   āyasmā: Āyasmā (nominative singular)
        *   ānando: Ānanda (nominative singular)
        *   bhagavantaṃ: Bhagavanta (accusative singular)
        *   etadavoca: said this (aorist 3rd person singular)
        *   Translation: To one side seated indeed Āyasmā Ānanda said this to Bhagavanta—

    *   *“acchariyaṃ, bhante, abbhutaṃ, bhante.*
        *   acchariyaṃ: wonderful! (exclamation)
        *   bhante: Bhante (vocative singular)
        *   abbhutaṃ: marvellous! (exclamation)
        *   bhante: Bhante (vocative singular)
        *   Translation: “Wonderful!, Bhante, marvellous!, Bhante.

    *   *Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca,*
        *   Yāva: As long as / how (adverb) - in this context "how" or "so much so".
        *   gambhīro: deep (adjective, masculine nominative singular)
        *   cāyaṃ: and this (ca + ayaṃ)
        *   bhante: Bhante (vocative singular)
        *   paṭiccasamuppādo: dependent origination (masculine nominative singular)
        *   gambhīrāvabhāso: appearing profound (adjective, masculine nominative singular)
        *   ca: and
        *   Translation: How deep indeed this, Bhante, dependent origination and profound in appearance,

    *   *atha ca pana me uttānakuttānako viya khāyatī”ti.*
        *   atha: and (or "then")
        *   ca: and
        *   pana: moreover/but
        *   me: to me (dative)
        *   uttānakuttānako: very clear (adjective, masculine nominative singular)
        *   viya: like (adverb/preposition)
        *   khāyatī: [it] eats / strived? (Wait, dictionary says "khā" is space/sky and "yati" is strived. But "khāyatī" is a single word in the text. Let's check dictionary: khā + yatī. "khā" (space/sky) + "yati" (strives). This is a metaphor: "striving in the sky"? Or "eating the sky"? Let's look at the dictionary provided: khā (space/sky) + yatī (strived). "khāyatī" is a sandhi. The dictionary says "khāyatī = khā + yatī". So "striving in the sky" or "striving through space".)
        *   ti: (end of direct speech)
        *   Translation: and moreover [it] is like a very clear striving in the sky”

    *   *“Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca.*
        *   Mā: Do not (indeclinable)
        *   hevaṃ: indeed thus (sandhi of hevaṃ)
        *   ānanda: Ānanda (vocative singular)
        *   avaca: said (imperfect 3rd person singular) - Wait, "Mā... avaca" is a command/prohibition. "Do not say thus".
        *   Translation: “Do not indeed thus, Ānanda, say, do not indeed thus, Ānanda, say.

    *   *Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca.*
        *   Gambhīro: Deep (adjective, masculine nominative singular)
        *   cāyaṃ: and this (ca + ayaṃ)
        *   ānanda: Ānanda (vocative singular)
        *   paṭiccasamuppādo: dependent origination (masculine nominative singular)
        *   gambhīrāvabhāso: appearing profound (adjective, masculine nominative singular)
        *   ca: and
        *   Translation: Deep indeed this, Ānanda, dependent origination and profound in appearance.

    *   *Etassa, ānanda, `dhamma` (teaching) ananub

<details><summary>raw draft and checker</summary>

<|channel>thought
*   Source: Pāli text.
    *   Target: English translation.
    *   Constraints:
        *   Literal and faithful, word by word as far as English allows.
        *   Render every word in the grammatical form given by dictionary analysis (case, number, tense, person, voice).
        *   Keep Pāli word order where English allows.
        *   Add nothing (no explanation, no commentary, no interpretation, no assumption of religion).
        *   Leave personal names, place names, and titles untranslated in stem form (Kammāsadhamma, Kuru, Ānanda).
        *   Leave honorifics/titles untranslated (Bhagavā, Bhante).
        *   Technical terms: Keep in backticks with a short English gloss on first occurrence (e.g., `paṭiccasamuppādo` (dependent origination)).
        *   Answer with the translation only.

    *   *Evaṃ me sutaṃ—*
        *   Evaṃ: thus
        *   me: by me (instrumental) / to me (dative) / me (accusative). In "Evaṃ me sutaṃ", it's usually "Thus by me [it was] heard".
        *   sutaṃ: heard (past participle, neuter nominative singular).
        *   Translation: Thus by me [it was] heard—

    *   *ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo.*
        *   ekaṃ: a
        *   samayaṃ: time (masculine accusative singular)
        *   bhagavā: Bhagavā (nominative singular)
        *   kurūsu: in Kuru (masculine locative plural)
        *   viharati: dwells (present 3rd person singular)
        *   kammāsadhammaṃ: Kammāsadhamma (neuter nominative singular)
        *   nāma: named
        *   kurūnaṃ: of Kuru (masculine genitive plural)
        *   nigamo: town (masculine nominative singular)
        *   Translation: a time Bhagavā dwells in Kuru, Kammāsadhamma named [is the] town of Kuru.
        *   Refining word order: a time Bhagavā dwells in Kuru, Kammāsadhamma named [is the] town of Kuru. (Wait, "nigamo" is the subject/complement).
        *   Let's look at the structure: "ekaṃ samayaṃ bhagavā kurūsu viharati [at] kammāsadhammaṃ nāma kurūnaṃ nigamo."
        *   Literal: a time Bhagavā in Kuru dwells, Kammāsadhamma named [is the] town of Kuru.

    *   *Atha kho āyasmā ānando yena bhagavā tenupasaṅkami,*
        *   Atha: Then
        *   kho: indeed
        *   āyasmā: Āyasmā (nominative singular)
        *   ānando: Ānanda (nominative singular)
        *   yena: by which / where
        *   bhagavā: Bhagavā (nominative singular)
        *   tenupasaṅkami: approached there (aorist 3rd person singular)
        *   Translation: Then indeed Āyasmā Ānanda, where Bhagavā [was], approached there,

    *   *upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi.*
        *   upasaṅkamitvā: having approached (absolutive)
        *   bhagavantaṃ: Bhagavanta (accusative singular)
        *   abhivādetvā: having bowed down (absolutive)
        *   ekamantaṃ: to one side (adverb)
        *   nisīdi: sat down (aorist 3rd person singular)
        *   Translation: having approached, having bowed down to Bhagavanta, [he] sat down to one side.

    *   *Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca—*
        *   Ekamantaṃ: To one side (adverb)
        *   nisinno: seated (past participle, masculine nominative singular)
        *   kho: indeed
        *   āyasmā: Āyasmā (nominative singular)
        *   ānando: Ānanda (nominative singular)
        *   bhagavantaṃ: Bhagavanta (accusative singular)
        *   etadavoca: said this (aorist 3rd person singular)
        *   Translation: To one side seated indeed Āyasmā Ānanda said this to Bhagavanta—

    *   *“acchariyaṃ, bhante, abbhutaṃ, bhante.*
        *   acchariyaṃ: wonderful! (exclamation)
        *   bhante: Bhante (vocative singular)
        *   abbhutaṃ: marvellous! (exclamation)
        *   bhante: Bhante (vocative singular)
        *   Translation: “Wonderful!, Bhante, marvellous!, Bhante.

    *   *Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca,*
        *   Yāva: As long as / how (adverb) - in this context "how" or "so much so".
        *   gambhīro: deep (adjective, masculine nominative singular)
        *   cāyaṃ: and this (ca + ayaṃ)
        *   bhante: Bhante (vocative singular)
        *   paṭiccasamuppādo: `paṭiccasamuppādo` (dependent origination) (masculine nominative singular)
        *   gambhīrāvabhāso: appearing profound (adjective, masculine nominative singular)
        *   ca: and
        *   Translation: How deep indeed this, Bhante, `paṭiccasamuppādo` (dependent origination) and profound in appearance,

    *   *atha ca pana me uttānakuttānako viya khāyatī”ti.*
        *   atha: and (or "then")
        *   ca: and
        *   pana: moreover/but
        *   me: to me (dative)
        *   uttānakuttānako: very clear (adjective, masculine nominative singular)
        *   viya: like (adverb/preposition)
        *   khāyatī: [it] eats / strived? (Wait, dictionary says "khā" is space/sky and "yati" is strived. But "khāyatī" is a single word in the text. Let's check dictionary: khā + yatī. "khā" (space/sky) + "yati" (strives). This is a metaphor: "striving in the sky"? Or "eating the sky"? Let's look at the dictionary provided: khā (space/sky) + yatī (strived). "khāyatī" is a sandhi. The dictionary says "khāyatī = khā + yatī". So "striving in the sky" or "striving through space".)
        *   ti: (end of direct speech)
        *   Translation: and moreover [it] is like a very clear striving in the sky”

    *   *“Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca.*
        *   Mā: Do not (indeclinable)
        *   hevaṃ: indeed thus (sandhi of hevaṃ)
        *   ānanda: Ānanda (vocative singular)
        *   avaca: said (imperfect 3rd person singular) - Wait, "Mā... avaca" is a command/prohibition. "Do not say thus".
        *   Translation: “Do not indeed thus, Ānanda, say, do not indeed thus, Ānanda, say.

    *   *Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca.*
        *   Gambhīro: Deep (adjective, masculine nominative singular)
        *   cāyaṃ: and this (ca + ayaṃ)
        *   ānanda: Ānanda (vocative singular)
        *   paṭiccasamuppādo: `paṭiccasamuppādo` (dependent origination) (masculine nominative singular)
        *   gambhīrāvabhāso: appearing profound (adjective, masculine nominative singular)
        *   ca: and
        *   Translation: Deep indeed this, Ānanda, `paṭiccasamuppādo` (dependent origination) and profound in appearance.

    *   *Etassa, ānanda, dhammassa ananub

- fixed: 'dhammassa': technical term left bare — written as `dhamma` (teaching)
- open: 'saṃsāraṃ': technical term (cycle of rebirth) not shown in the `word` (gloss) form — write it as `saṃsāraṃ` (cycle of rebirth) on its first occurrence, then 'cycle of rebirth'
- open: 'nātivattati': present tense (present-tense verb (from na ativattati); present 3rd person singular) may have been rendered as past — use the present: 'does not overstep'

</details>


### Paragraph 2

> ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

**mitra-qwen35-translate-mlx-bf16** (7s)

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**Qwen3.8-27B-8bit** (194s)

We need answer user's request: translate Pali into English literally and faithfully, word by word as far as English allows. Need use dictionary analysis. Need output translation only. Need think in English because user request English? User is English. Need produce final only translation.

We need parse Pali:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

Need render every word, keep Pali order where English allows, no additions. Need technical terms: jarāmaraṇa (old age and death), jāti (birth) maybe in compounds? Rule: Where word used as technical term, keep it as it stands in text in backticks with short English gloss on first occurrence. Candidates include jarāmaraṇa (old age and death), jāti (birth). But text has jarāmaraṇan’ti, jātipaccayā. Need decide how to render technical terms. It says keep it as it stands in the text in backticks with a short English gloss in parentheses on its first occurrence, like `viññāṇaṃ` (consciousness), and use plain gloss afterwards. Candidates in this text: ... jarāmaraṇa (old age and death), ... jāti (birth). So first occurrence of jarāmaraṇa should be `jarāmaraṇan`? It says as it stands in text. The word is jarāmaraṇan’ti (elided vowel). Maybe keep `jarāmaraṇan`? The text has jarāmaraṇan’ti. Need render every word. Could translate: “There is old age and death due to this,” thus asked, being present, Ānanda, it should be said: “There is.” If he would say, “Due to what condition is old age and death?” thus, “Due to birth is old age and death” should be said to him.

But need literal word order and render particles: iti, ce, iccassa etc. Need include all words. Let's parse carefully.

Sentence 1:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.

Words:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.

Atthi: there is.
idappaccayā: due to this / on account of this (ablative adverb).
jarāmaraṇan’ti: jarāmaraṇa + ti? The ti is quotative particle? Dictionary says ti 3 verbal ending? But in Pali, -nti often quotative? Actually jarāmaraṇan’ti = jarāmaraṇaṃ ti? The n before ti is sandhi: jarāmaraṇan ti. It means "old age and death" (accusative? jarāmaraṇaṃ) + ti quotative. Dictionary analysis says elided vowel, jarāmaraṇan not in DPD, ti verbal ending? But likely quotative. Need render as quoted phrase: “There is old age and death due to this.” The ti marks quote. iti also thus. puṭṭhena satā: asked, being present? Actually puṭṭhena satā = "being asked" (instrumental absolute). satā from santa present participle instrumental singular: existing, being present. puṭṭhena satā = "being asked" or "when asked". Need literal: "asked, being present"? The dictionary gives puṭṭhena asked; satā existing/being present. Could render "asked, being present". But in Pali absolute: puṭṭhena satā = "having been asked" or "being asked". Need keep every word: puṭṭhena (asked) satā (being present). Maybe "asked, being present". But "satā" could be "being" (santa). Need not add.

ānanda: vocative, keep Ānanda.
atthītissa: = atthi + iti + assa? Actually atthi + ti + assa? The phrase: atthītissa vacanīyaṃ. It means "it should be said: 'There is.'" atthi iti assa vacanīyaṃ? Let's parse: atthi (there is) + iti (thus) + assa (to him? dative singular of ta? or optative of atthi?) The dictionary says atthītissa = atthi + iti + assa, sandhi/compound. Components: atthi there is; iti thus; assa optative of atthi? may be? But likely pronoun assa = to him (dative singular of ta). In Pali, atthi iti assa vacanīyaṃ = "to him it should be said: 'There is.'" The assa is dative pronoun "to him". Dictionary analysis for assa includes optative verb of atthi, but also likely pronoun? It only lists optative and horse. But in context, atthi iti assa vacanīyaṃ: "to him it should be said, 'There is.'" The sandhi atthi + iti + assa = atthītissa? Actually atthi iti assa -> atthi iti assa, with sandhi: atthi + iti = atthīti? then + assa = atthītissa? Yes. So atthi (there is) iti (thus) assa (to him). Need render every word: "there is" thus to him should be said. But English order: "to him it should be said: 'There is.'" Need include iti as thus? Rule render every particle, iti rendered. Could say: "‘There is,’ thus to him should be said." But need natural? Literal.

vacanīyaṃ: should be said (neuter nom/acc). Subject? "it should be said".

So first sentence: “There is old age and death due to this,” thus asked, being present, Ānanda, “there is” thus to him should be said.

But need technical term jarāmaraṇa first occurrence in backticks with gloss. The quoted phrase: ‘Atthi idappaccayā jarāmaraṇan’ti. If we keep technical term as it stands: `jarāmaraṇan`? The text has jarāmaraṇan’ti. Maybe we can render: “There is `jarāmaraṇa` (old age and death) due to this,”? But rule says keep it as it stands in the text in backticks. The word in text is jarāmaraṇan’ti, not jarāmaraṇa. But the technical term is jarāmaraṇa. The candidate list says jarāmaraṇa (old age and death). It might expect first occurrence: `jarāmaraṇan` (old age and death)? But "as it stands in the text" maybe use the exact Pali word form, including case ending. Example: consciousness uses exact form with ṃ. So for jarāmaraṇan’ti, the word is jarāmaraṇan (with ti separate? The table says jarāmaraṇan’ti = jarāmaraṇan + ti, elided vowel. So exact form is jarāmaraṇan? But in text it's jarāmaraṇan’ti. Could backtick old age and death and then ti? But need render ti. Maybe: “There is old age and death thus due to this,”? Hmm.

Need decide final translation style. The instruction: "You translate Pāli into English literally and faithfully, word by word as far as English allows. You render every word in the grammatical form the dictionary analysis gives (case, number, tense, person, voice), keep the Pāli word order where English allows, and add nothing that is not in the Pāli: no explanation, no commentary, no interpretation, and no assumption that the text is religious unless its words say so. You answer with the translation only."

Also rules: render every word; drop no particle (ca, vā, pi, eva, hi, kho, pana, iti are all rendered). Leave personal names... technical terms keep as it stands in text in backticks with short English

<details><summary>raw draft and checker</summary>

We need answer user's request: translate Pali into English literally and faithfully, word by word as far as English allows. Need use dictionary analysis. Need output translation only. Need think in English because user request English? User is English. Need produce final only translation.

We need parse Pali:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

Need render every word, keep Pali order where English allows, no additions. Need technical terms: jarāmaraṇa (old age and death), jāti (birth) maybe in compounds? Rule: Where word used as technical term, keep it as it stands in text in backticks with short English gloss on first occurrence. Candidates include jarāmaraṇa (old age and death), jāti (birth). But text has jarāmaraṇan’ti, jātipaccayā. Need decide how to render technical terms. It says keep it as it stands in the text in backticks with a short English gloss in parentheses on its first occurrence, like `viññāṇaṃ` (consciousness), and use plain gloss afterwards. Candidates in this text: ... jarāmaraṇa (old age and death), ... jāti (birth). So first occurrence of jarāmaraṇa should be `jarāmaraṇan`? It says as it stands in text. The word is jarāmaraṇan’ti (elided vowel). Maybe keep `jarāmaraṇan`? The text has jarāmaraṇan’ti. Need render every word. Could translate: “There is old age and death due to this,” thus asked, being present, Ānanda, it should be said: “There is.” If he would say, “Due to what condition is old age and death?” thus, “Due to birth is old age and death” should be said to him.

But need literal word order and render particles: iti, ce, iccassa etc. Need include all words. Let's parse carefully.

Sentence 1:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.

Words:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.

Atthi: there is.
idappaccayā: due to this / on account of this (ablative adverb).
jarāmaraṇan’ti: jarāmaraṇa + ti? The ti is quotative particle? Dictionary says ti 3 verbal ending? But in Pali, -nti often quotative? Actually jarāmaraṇan’ti = jarāmaraṇaṃ ti? The n before ti is sandhi: jarāmaraṇan ti. It means "old age and death" (accusative? jarāmaraṇaṃ) + ti quotative. Dictionary analysis says elided vowel, jarāmaraṇan not in DPD, ti verbal ending? But likely quotative. Need render as quoted phrase: “There is old age and death due to this.” The ti marks quote. iti also thus. puṭṭhena satā: asked, being present? Actually puṭṭhena satā = "being asked" (instrumental absolute). satā from santa present participle instrumental singular: existing, being present. puṭṭhena satā = "being asked" or "when asked". Need literal: "asked, being present"? The dictionary gives puṭṭhena asked; satā existing/being present. Could render "asked, being present". But in Pali absolute: puṭṭhena satā = "having been asked" or "being asked". Need keep every word: puṭṭhena (asked) satā (being present). Maybe "asked, being present". But "satā" could be "being" (santa). Need not add.

ānanda: vocative, keep Ānanda.
atthītissa: = atthi + iti + assa? Actually atthi + ti + assa? The phrase: atthītissa vacanīyaṃ. It means "it should be said: 'There is.'" atthi iti assa vacanīyaṃ? Let's parse: atthi (there is) + iti (thus) + assa (to him? dative singular of ta? or optative of atthi?) The dictionary says atthītissa = atthi + iti + assa, sandhi/compound. Components: atthi there is; iti thus; assa optative of atthi? may be? But likely pronoun assa = to him (dative singular of ta). In Pali, atthi iti assa vacanīyaṃ = "to him it should be said: 'There is.'" The assa is dative pronoun "to him". Dictionary analysis for assa includes optative verb of atthi, but also likely pronoun? It only lists optative and horse. But in context, atthi iti assa vacanīyaṃ: "to him it should be said, 'There is.'" The sandhi atthi + iti + assa = atthītissa? Actually atthi iti assa -> atthi iti assa, with sandhi: atthi + iti = atthīti? then + assa = atthītissa? Yes. So atthi (there is) iti (thus) assa (to him). Need render every word: "there is" thus to him should be said. But English order: "to him it should be said: 'There is.'" Need include iti as thus? Rule render every particle, iti rendered. Could say: "‘There is,’ thus to him should be said." But need natural? Literal.

vacanīyaṃ: should be said (neuter nom/acc). Subject? "it should be said".

So first sentence: “There is old age and death due to this,” thus asked, being present, Ānanda, “there is” thus to him should be said.

But need technical term jarāmaraṇa first occurrence in backticks with gloss. The quoted phrase: ‘Atthi idappaccayā jarāmaraṇan’ti. If we keep technical term as it stands: `jarāmaraṇan`? The text has jarāmaraṇan’ti. Maybe we can render: “There is `jarāmaraṇa` (old age and death) due to this,”? But rule says keep it as it stands in the text in backticks. The word in text is jarāmaraṇan’ti, not jarāmaraṇa. But the technical term is jarāmaraṇa. The candidate list says jarāmaraṇa (old age and death). It might expect first occurrence: `jarāmaraṇan` (old age and death)? But "as it stands in the text" maybe use the exact Pali word form, including case ending. Example: `viññāṇaṃ` (consciousness) uses exact form with ṃ. So for jarāmaraṇan’ti, the word is jarāmaraṇan (with ti separate? The table says jarāmaraṇan’ti = jarāmaraṇan + ti, elided vowel. So exact form is jarāmaraṇan? But in text it's jarāmaraṇan’ti. Could backtick `jarāmaraṇan` (old age and death) and then ti? But need render ti. Maybe: “There is `jarāmaraṇan` (old age and death) thus due to this,”? Hmm.

Need decide final translation style. The instruction: "You translate Pāli into English literally and faithfully, word by word as far as English allows. You render every word in the grammatical form the dictionary analysis gives (case, number, tense, person, voice), keep the Pāli word order where English allows, and add nothing that is not in the Pāli: no explanation, no commentary, no interpretation, and no assumption that the text is religious unless its words say so. You answer with the translation only."

Also rules: render every word; drop no particle (ca, vā, pi, eva, hi, kho, pana, iti are all rendered). Leave personal names... technical terms keep as it stands in text in backticks with short English



</details>

**gemma-4-26B-A4B-it-qat-8bit** (39s)

<|channel>thought
*   "‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ."

    *   `Atthi`: 3rd person singular present of *atthi*: "there is" or "there exists".
    *   `idappaccayā`: ablative singular of *idappaccaya*: "due to this [condition]" or "because of this".
    *   `jarāmaraṇan'ti`: *jarāmaraṇa* (old age and death) + *iti* (quotation marker).
    *   `iti`: "thus" or "this is".
    *   `puṭṭhena`: instrumental singular of *puṭṭha* (past participle of *pucchati*): "by/with being asked".
    *   `satā`: instrumental singular of *santa* (present participle of *atthi*): "being" or "existing".
    *   `ānanda`: vocative singular of *Ānanda*: "Ānanda".
    *   `atthītissa`: *atthi* (there is) + *iti* (thus) + *assa* (to him/for him - optative/dative context). Looking at the dictionary: *assa* is optative 3rd person singular "may be" OR masculine nominative/vocative "horse". Wait, the dictionary says `atthītissa` = `atthi + iti + assa`. *Assa* is the dative/locative singular of *assa* (horse) or the optative of *atthi*. However, in this context, it's likely a sandhi form related to the previous clause. Let's look at the structure: `Atthi idappaccayā jarāmaraṇan'ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.`
        *   `puṭṭhena satā`: "by being asked".
        *   `atthītissa vacanīyaṃ`: `atthi` (there is) + `iti` (thus) + `assa` (to him). So, "should be said to him thus [that] there is".
        *   Wait, let's re-examine `atthītissa`. The dictionary says `assa` is optative 3rd person singular "may be" or "horse". But in the context of `vacanīyaṃ` (should be said), it's likely "to him" (dative of *assa* - though *assa* is usually a noun, the pronoun *assa* is dative of *taṃ*). Actually, `assa` is the dative singular of the pronoun *taṃ* (him/it). The dictionary provided says `assa` is optative or "horse". I must follow the dictionary provided.
        *   Dictionary for `assa`: 3.1: optative verb "may be"; 1.1: masculine noun "horse".
        *   Wait, the dictionary says `atthītissa` = `atthi + iti + assa`.
        *   Let's look at the whole sentence: "‘There is due to this condition `jarāmaraṇa` (old age and death),’ thus, by being asked, Ānanda, should be said to him [as] there is."
        *   Actually, `atthītissa` might be `atthi + iti + assa`. If `assa` is "may be", then "should be said to him [that] there is thus".
        *   Let's look at the second sentence: `‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.`
        *   `Kiṃpaccayā`: "due to what condition?".
        *   `jarāmaraṇan'ti`: "old age and death, thus".
        *   `iti`: "thus".
        *   `ce`: "if".
        *   `vadeyya`: "he would say".
        *   `jātipaccayā`: "due to birth".
        *   `jarāmaraṇan'ti`: "old age and death, thus".
        *   `iccassa`: "thus to him".
        *   `vacanīyaṃ`: "should be said".

    *   Sentence 1: `‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.`
        *   `Atthi`: There is
        *   `idappaccayā`: due to this condition
        *   `jarāmaraṇan'ti`: old age and death, thus
        *   `iti`: [quotation marker]
        *   `puṭṭhena`: by being asked
        *   `satā`: being
        *   `ānanda`: Ānanda
        *   `atthītissa`: [atthi + iti + assa] -> "there is thus may be" (This is tricky. Let's look at the grammar again).
        *   If `assa` is optative "may be", then `atthītissa` = "there is thus may be".
        *   `vacanīyaṃ`: should be said.
        *   Let's re-read: "‘There is due to this condition old age and death,’ thus, by being asked, Ānanda, should be said to him [that] there is thus."
        *   Wait, the dictionary says `assa` is optative "may be". If I follow the dictionary strictly: `atthītissa` = "there is thus may be".
        *   Let's look at the structure again. `Atthi idappaccayā jarāmaraṇan'ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.`
        *   "‘There is due to this condition old age and death,’ thus, by being asked, Ānanda, should be said to him [that] there is thus."
        *   Actually, `assa` in Pāli often functions as the dative of *taṃ* (him). The dictionary provided says `assa` is optative or "horse". I must stick to the dictionary.
        *   If `assa` is optative "may be", then `atthītissa` = "there is thus may be".
        *   "‘There is due to this condition old age and death,’ thus, by being asked, Ānanda, should be said [that] there is thus may be."
        *   Wait, `atthītissa` = `atthi` + `iti` + `assa`.
        *   Let's try to find a more natural way that respects the "word by word" rule.
        *   `Atthi`: There is
        *   `idappaccayā`: due to this condition
        *   `jarāmaraṇan'ti`: old age and death, thus
        *   `iti`: thus
        *   `puṭṭhena`: by being asked
        *   `satā`: being
        *   `ānanda`: Ānanda
        *   `atthītissa`: there is thus may be (following the dictionary)
        *   `vacanīyaṃ`: should be said.

    *   Sentence 2: `‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.`
        *   `Kiṃpaccayā`: Due to what condition?
        *   `jarāmaraṇan'ti`: old age and death, thus
        *   `iti`: thus
        *   `ce`: if
        *   `vadeyya`: he would say
        *   `jātipaccayā`: due to birth
        *   `jarāmaraṇan'ti`: old age and death, thus
        *   `iccassa`: thus to him
        *   `vacanīyaṃ`: should be said.

    *   "‘There is due to this condition old age and death,’ thus, by being asked, Ānanda, should be said [that] there is thus may be. ‘Due to what condition old age and death,’ thus if he would say, ‘due to birth old age and death,’ thus to him should be said."

    *   Wait, let's look at `atthītissa` again. In many Pāli texts, `assa` is the dative of *taṃ*.

<details><summary>raw draft and checker</summary>

<|channel>thought
*   "‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ."

    *   `Atthi`: 3rd person singular present of *atthi*: "there is" or "there exists".
    *   `idappaccayā`: ablative singular of *idappaccaya*: "due to this [condition]" or "because of this".
    *   `jarāmaraṇan'ti`: *jarāmaraṇa* (old age and death) + *iti* (quotation marker).
    *   `iti`: "thus" or "this is".
    *   `puṭṭhena`: instrumental singular of *puṭṭha* (past participle of *pucchati*): "by/with being asked".
    *   `satā`: instrumental singular of *santa* (present participle of *atthi*): "being" or "existing".
    *   `ānanda`: vocative singular of *Ānanda*: "Ānanda".
    *   `atthītissa`: *atthi* (there is) + *iti* (thus) + *assa* (to him/for him - optative/dative context). Looking at the dictionary: *assa* is optative 3rd person singular "may be" OR masculine nominative/vocative "horse". Wait, the dictionary says `atthītissa` = `atthi + iti + assa`. *Assa* is the dative/locative singular of *assa* (horse) or the optative of *atthi*. However, in this context, it's likely a sandhi form related to the previous clause. Let's look at the structure: `Atthi idappaccayā jarāmaraṇan'ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.`
        *   `puṭṭhena satā`: "by being asked".
        *   `atthītissa vacanīyaṃ`: `atthi` (there is) + `iti` (thus) + `assa` (to him). So, "should be said to him thus [that] there is".
        *   Wait, let's re-examine `atthītissa`. The dictionary says `assa` is optative 3rd person singular "may be" or "horse". But in the context of `vacanīyaṃ` (should be said), it's likely "to him" (dative of *assa* - though *assa* is usually a noun, the pronoun *assa* is dative of *taṃ*). Actually, `assa` is the dative singular of the pronoun *taṃ* (him/it). The dictionary provided says `assa` is optative or "horse". I must follow the dictionary provided.
        *   Dictionary for `assa`: 3.1: optative verb "may be"; 1.1: masculine noun "horse".
        *   Wait, the dictionary says `atthītissa` = `atthi + iti + assa`.
        *   Let's look at the whole sentence: "‘There is due to this condition `jarāmaraṇa` (old age and death),’ thus, by being asked, Ānanda, should be said to him [as] there is."
        *   Actually, `atthītissa` might be `atthi + iti + assa`. If `assa` is "may be", then "should be said to him [that] there is thus".
        *   Let's look at the second sentence: `‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.`
        *   `Kiṃpaccayā`: "due to what condition?".
        *   `jarāmaraṇan'ti`: "`jarāmaraṇa` (old age and death), thus".
        *   `iti`: "thus".
        *   `ce`: "if".
        *   `vadeyya`: "he would say".
        *   `jātipaccayā`: "due to birth".
        *   `jarāmaraṇan'ti`: "`jarāmaraṇa` (old age and death), thus".
        *   `iccassa`: "thus to him".
        *   `vacanīyaṃ`: "should be said".

    *   Sentence 1: `‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.`
        *   `Atthi`: There is
        *   `idappaccayā`: due to this condition
        *   `jarāmaraṇan'ti`: `jarāmaraṇa` (old age and death), thus
        *   `iti`: [quotation marker]
        *   `puṭṭhena`: by being asked
        *   `satā`: being
        *   `ānanda`: Ānanda
        *   `atthītissa`: [atthi + iti + assa] -> "there is thus may be" (This is tricky. Let's look at the grammar again).
        *   If `assa` is optative "may be", then `atthītissa` = "there is thus may be".
        *   `vacanīyaṃ`: should be said.
        *   Let's re-read: "‘There is due to this condition `jarāmaraṇa` (old age and death),’ thus, by being asked, Ānanda, should be said to him [that] there is thus."
        *   Wait, the dictionary says `assa` is optative "may be". If I follow the dictionary strictly: `atthītissa` = "there is thus may be".
        *   Let's look at the structure again. `Atthi idappaccayā jarāmaraṇan'ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.`
        *   "‘There is due to this condition `jarāmaraṇa` (old age and death),’ thus, by being asked, Ānanda, should be said to him [that] there is thus."
        *   Actually, `assa` in Pāli often functions as the dative of *taṃ* (him). The dictionary provided says `assa` is optative or "horse". I must stick to the dictionary.
        *   If `assa` is optative "may be", then `atthītissa` = "there is thus may be".
        *   "‘There is due to this condition `jarāmaraṇa` (old age and death),’ thus, by being asked, Ānanda, should be said [that] there is thus may be."
        *   Wait, `atthītissa` = `atthi` + `iti` + `assa`.
        *   Let's try to find a more natural way that respects the "word by word" rule.
        *   `Atthi`: There is
        *   `idappaccayā`: due to this condition
        *   `jarāmaraṇan'ti`: `jarāmaraṇa` (old age and death), thus
        *   `iti`: thus
        *   `puṭṭhena`: by being asked
        *   `satā`: being
        *   `ānanda`: Ānanda
        *   `atthītissa`: there is thus may be (following the dictionary)
        *   `vacanīyaṃ`: should be said.

    *   Sentence 2: `‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.`
        *   `Kiṃpaccayā`: Due to what condition?
        *   `jarāmaraṇan'ti`: `jarāmaraṇa` (old age and death), thus
        *   `iti`: thus
        *   `ce`: if
        *   `vadeyya`: he would say
        *   `jātipaccayā`: due to birth
        *   `jarāmaraṇan'ti`: `jarāmaraṇa` (old age and death), thus
        *   `iccassa`: thus to him
        *   `vacanīyaṃ`: should be said.

    *   "‘There is due to this condition `jarāmaraṇa` (old age and death),’ thus, by being asked, Ānanda, should be said [that] there is thus may be. ‘Due to what condition `jarāmaraṇa` (old age and death),’ thus if he would say, ‘due to birth `jarāmaraṇa` (old age and death),’ thus to him should be said."

    *   Wait, let's look at `atthītissa` again. In many Pāli texts, `assa` is the dative of *taṃ*.



</details>


## As reviewer (of the first translator's checked draft)

| model | mean s/para | parsed | issues reported | open findings resolved |
| --- | --- | --- | --- | --- |
| Qwen3.8-27B-8bit | 394 | 0/2 | 0 | 0/2 |
| gemma-4-26B-A4B-it-qat-8bit | 81 | 0/2 | 0 | 0/2 |

### Paragraph 1 — reviewed draft

Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth).”

Open findings handed to the reviewer:
- 'Yāva': particle meaning 'as long as; as far as; so much so; up to; until; from… to' is not rendered — render it (for example 'as long as') where it stands in the sentence
- 'dhammassa': technical term (teaching) not shown in the `word` (gloss) form — write it as `dhamma` (teaching) on its first occurrence, then 'teaching'

**Qwen3.8-27B-8bit** (417s; issues: 0; still open: 2)


Revised: Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth).”

<details><summary>unparsed output</summary>

```
We need answer user's request. Need review Pali-to-English translation segment [1] only? They provide segments to check: Segment [1] only. Need output exactly form ISSUES, REVISED with [1] complete revised translation. Need fix listed problems and any other issues? They say Problems already found MUST be fixed. We are meticulous reviewer. Need ensure all rules. Need likely only segment 1. Need produce one line per segment? They say one line per segment, every segment repeated even if unchanged, in same numbering; a segment that contains line breaks keeps them, with [n] marker only on its first line. But segment 1 translation has line breaks? Original translation includes blank line between quotes? It is one segment with line break. Need revised [1] can contain line breaks? They say a segment that contains line breaks keeps them, with [n] marker only on its first line. So output REVISED:
[1] Thus have I heard... (maybe with line break after first quote? Need preserve? The original segment translation has a blank line between the two quoted parts. It says Markdown formatting and any %%number%% placeholders stay exactly where they are. There are no placeholders. Need maybe keep line breaks? The segment as given includes a blank line after first quote and before second quote. We should keep line breaks? It says segment that contains line breaks keeps them. So include blank line? In final, after [1] first line, then maybe second line? But they also say one line per segment? Contra
```

</details>

**gemma-4-26B-A4B-it-qat-8bit** (85s; issues: 0; still open: 2)


Revised: Thus have I heard: at one time the Bhagavā dwells among the Kurus, in a market town of the Kurus named Kammāsadhamma. Then the Venerable Ānanda approached the Bhagavā; having approached and paid homage to the Bhagavā, he sat down to one side. Sitting to one side, the Venerable Ānanda said this to the Bhagavā: “It is wonderful, Bhante! It is marvelous, Bhante! How deep this `paṭiccasamuppādo` (dependent origination) is, Bhante, and how deep it appears; yet to me it seems as plain as the surface of a pond.”

“Do not say that, Ānanda! Do not say that, Ānanda! This dependent origination is indeed deep and appears deep. It is through the non-comprehension and non-penetration of this Dhamma, Ānanda, that this generation has become like a tangled skein, like a knotted ball of thread, like matted rushes and reeds; it does not transcend the plane of misery, the bad destination, the lower realms, and the `saṃsāraṃ` (cycle of rebirth).”

<details><summary>unparsed output</summary>

```
<|channel>thought
*   Rule 1: Literal and faithful (every word, grammatical form). No additions, omissions, or paraphrasing.
    *   Rule 2: No commentary/interpretation/religious assumption.
    *   Rule 3: Names (Kammāsadhamma, Kuru, Ānanda) and honorifics (Bhagavā, Bhante) stay untranslated in stem form.
    *   Rule 4: Technical terms in backticks with gloss on first occurrence, then plain gloss.
    *   Rule 5: Particles (ca, vā, pi, eva, hi, kho, pana, iti) must be rendered.
    *   Rule 6: Markdown and %%number%% placeholders stay.
    *   Rule 7: Consistency.

    *   Pāli: `Evaṃ me sutaṃ— ekaṃ samayaṃ bhagavā kurūsu viharati kammāsadhammaṃ nāma kurūnaṃ nigamo. Atha kho āyasmā ānando yena bhagavā tenupasaṅkami, upasaṅkamitvā bhagavantaṃ abhivādetvā ekamantaṃ nisīdi. Ekamantaṃ nisinno kho āyasmā ānando bhagavantaṃ etadavoca— “acchariyaṃ, bhante, abbhutaṃ, bhante. Yāva gambhīro cāyaṃ, bhante, paṭiccasamuppādo gambhīrāvabhāso ca, atha ca pana me uttānakuttānako viya khāyatī”ti. “Mā hevaṃ, ānanda, avaca, mā hevaṃ, ānanda, avaca. Gambhīro cāyaṃ, ānanda, paṭiccasamuppādo gambhīrāvabhāso ca. Etassa, ānanda, dhammassa ananubodhā appaṭivedhā evamayaṃ pajā tantākulakajātā kulagaṇṭhikajātā muñjapabbajabhūtā apāyaṃ duggatiṃ vinipātaṃ saṃsāraṃ nātivattati.`

    *   *Evaṃ me sutaṃ*: Thus (evaṃ) me (to me/by me - here "I have heard" is the standard translation, but let's look at grammar: *me* is 1st person dative/instrumental/accusative. In "Evaṃ me sutaṃ", *me* is usually interpre
```

</details>


### Paragraph 2 — reviewed draft

“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

**Qwen3.8-27B-8bit** (370s; issues: 0; still open: 0)


Revised: “Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

<details><summary>unparsed output</summary>

```
We need answer user's request. Need review Pali translation segment 1 only? They provide segments to check: Segment [1] only. Need output exactly form ISSUES: ... REVISED: [1] ... END. Need ensure no extra.

We need analyze translation against rules. Pali:
‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

Translation:
“Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

Need check literal faithful. Words:
Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.
Break: Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ.
Maybe: "Ānanda, when asked 'Is there old age and death due to this?' one should say 'There is.'" Let's parse.
Atthi = there is. idappaccayā = due to this / on account of this (ablative? indeclinable). jarāmaraṇan’ti = old age and death + ti (quotative? maybe "old age and death" as quoted). iti = thus. puṭṭhena satā = when asked (instrumental absolute? puṭṭhena satā: having been asked). ānanda vocative. atthītissa = atthi + iti + assa? "there is" thus to him? vacanīyaṃ = should be said.
So first sentence: "Ānanda, when asked 'Is there old age and death due to this?' one should say to
```

</details>

**gemma-4-26B-A4B-it-qat-8bit** (76s; issues: 0; still open: 0)


Revised: “Ānanda, when asked: ‘Is there a specific condition for old age and death?’ one should say: ‘There is.’ If it should be asked: ‘With what as condition is there old age and death?’ one should say to him: ‘With birth as condition, there is old age and death.’”

<details><summary>unparsed output</summary>

```
<|channel>thought
*   Segment [1]: ‘Atthi idappaccayā jarāmaraṇan’ti iti puṭṭhena satā, ānanda, atthītissa vacanīyaṃ. ‘Kiṃpaccayā jarāmaraṇan’ti iti ce vadeyya, ‘jātipaccayā jarāmaraṇan’ti iccassa vacanīyaṃ.

    *   `Atthi`: 3rd person singular present verb: "there is".
    *   `idappaccayā`: ablative singular of `idappaccaya`: "due to this [condition]".
    *   `jarāmaraṇan'ti`: `jarāmaraṇa` (old age and death) + `iti`.
    *   `iti`: "thus" or used as a quotation marker.
    *   `puṭṭhena`: instrumental singular of `puṭṭha`: "by/with being asked".
    *   `satā`: instrumental singular of `santa`: "being" (present participle).
    *   `ānanda`: vocative singular: "Ānanda".
    *   `atthītissa`: `atthi` (there is) + `iti` (thus) + `assa` (to him/for him - optative 3rd person singular "may be"). Wait, let's look at the DPD analysis provided.
        *   `atthītissa` = `atthi` + `iti` + `assa`.
        *   `assa`: optative 3rd person singular "may be" OR masculine vocative singular "horse".
        *   Wait, the DPD says `assa` 3.1 is optative 3rd person singular "may be".
        *   `atthītissa`: `atthi` (there is) + `iti` (thus) + `assa` (may be). This looks like a complex construction. Let's re-examine the segment.
        *   `atthītissa vacanīyaṃ`: "it is to be said thus: 'there is'".
        *   Wait, `atthītissa` = `atthi` + `iti` + `assa`. If `assa` is optative 3rd person singular "may be", then `atthītissa` = "there is thus may be"? That doesn't make sense.
        *
```

</details>
