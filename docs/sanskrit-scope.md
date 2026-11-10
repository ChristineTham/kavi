# Extending Kavi to Sanskrit and Buddhist Hybrid Sanskrit: scope

Written 2026-11-03 after reviewing the sources the author named (Edgerton's grammar, the Buddhist Hybrid Sanskrit
dictionary at gandhari.org, vidyut, the ambuda data repository, the Cologne Digital Sanskrit Dictionaries) and testing
the tools on this Mac. Every fact below was checked in the source itself; the licences are quoted from the data files.

## 1. What Kavi does today, and what is Pāḷi-specific

Kavi's pipeline is: Markdown segmentation → word analysis → a translation model fed the analysis as reference →
an instruction-tuned reviewer → a deterministic checker → interlinear output in the textbook's symbols. Of these,
only the segmentation, the model loop and the output shapes are language-neutral. The Pāḷi is in four places:

| module | Pāḷi assumption |
| --- | --- |
| `dpd.py` | the Digital Pāḷi Dictionary is lexicon, morphology (1.28 M inflected forms with parses), compound analysis and sandhi deconstructor in one database |
| `sandhi.py` | the reverse-sandhi heuristics are Kaccāyana's Sandhikappa |
| `glossary.py`, `glossaries/default.txt`, `lint.py` | the renderings, honorifics and technical terms are the Pāḷi glossary's; the checker's variants are DPD meanings |
| `grammar.py`, `interlinear.py` | the symbols map the DPD's grammar abbreviations; the prompts say "Pāli" |

MITRA-QWEN, the translate model, is not an obstacle: its card lists Sanskrit among its source languages, Sanskrit →
English scores GEMBA 85.1, the highest of its English directions (Pāḷi → English 82.2), and the prompt template is
language-agnostic (the source text and the target language only). Buddhist Hybrid Sanskrit is not mentioned on the
card; the Dharmamitra corpora it was trained on include the BHS canon, so this is a matter for evaluation.

## 2. The sources reviewed

### Edgerton, Buddhist Hybrid Sanskrit Grammar (1953), the Markdown conversion

`buddhism-texts/markdown/Sanskrit/Franklin Edgerton (1953) - Buddhist Hybrid Sanskrit Grammar.md`: 1.8 MB, 15,015
lines, 392 headings, every paragraph numbered `**N.M.**` as in the print, with an errata file and a per-page proof
record beside it (the conversion was proofread page by page). The table of contents (lines 37–1418) is itself a map
of the deviations: chapters 2–3 phonology (consonant assimilation, `ch`, `kṣ`, voicing, aspirates, the law of morae,
long for short and short for long vowels, `u` for `am`, `e` for `aya`, `o` for `ava`, epenthetic vowels), chapter 4
sandhi (loss of initial and final vowels, `a` for `as`/`am`, hiatus bridgers `m r d n y`), chapters 5–7 number,
gender and case syntax (nominative absolute, instrumental for locative, genitive for dative …), chapters 8–21 the
noun and pronoun inflections ending by ending (for `a`-stems alone §§ 8.18–8.111: nominative singular in `-o -u -ū
-a -ā -e -aṃ`, instrumental `-enā -inā -asā -ayā`, ablative `-āto -ato -asmā`, locative `-i -aṃhi -asmiṃ -esmiṃ`,
nominative plural `-ā -a -e -i -āyo -āni`, instrumental plural `-ehi -ebhi`, genitive plural `-āna -ānaṃ`, and so
on), chapter 22 suffixes, 23 compounds, 24–43 the verb (thematic treatment, non-Sanskritic presents, the optative in
`-eya -eyā -e -i`, imperative, future, aorist incl. `-etsu(ḥ)`, perfect, participles, gerund `-tvāna -iya -yā`,
infinitive, voice, `-e-` stems and causatives), with § 20.63 a table of personal pronouns, § 21.46/85 paradigms and
chapter 43 a synopsis of verb forms by root. The paragraph numbers and the chapter structure make the grammar
machine-indexable: a rule can be cited as `Edg. § 8.108`.

### Edgerton's dictionary (BHSD)

Two copies exist. **gandhari.org** (`/dictionary?section=bhsd`) is a JavaScript application (Baums and Glass's
Gāndhārī site) that serves Edgerton's dictionary beside its own Dictionary of Gāndhārī, Monier-Williams, the PTS
dictionary and others; its entries come from undocumented PHP loaders (`lemmaLoader.php`, `itemLoader.php`,
`searchLoader.php`), it offers no download or stated licence, and its Preface says nothing about the BHSD's terms.
It is the right place to *read* an entry, not a data source. **Cologne** carries the same work as `BHS`
("Edgerton Buddhist Hybrid Sanskrit Dictionary, 1953"): `bhs.txt`, 7.6 MB, 17,839 entries in a documented markup
(`<L>` record, `<pc>` page-column, `<k1>` headword in SLP1, `<k2>` the printed headword, `{@bold@}`, `{%italic%}`,
`<ls>` literary source, `〔…〕` references, `<lang>Pali</lang>` for the Pāḷi cognate that most entries give), with an
XML version by headword and a header that licenses the digitisation CC BY-NC-SA 3.0 (The Sanskrit Library and Thomas
Malten); the git repository `sanskrit-lexicon/csl-orig` that holds it is CC BY-SA 4.0. The entries' Pāḷi cognates
are a bridge to the DPD and to the existing glossary.

### vidyut (ambuda-org)

A Rust toolkit with Python bindings (`vidyut` 0.4.0 on PyPI, January 2025, MIT; macOS arm64 wheels; installs with
`uv add vidyut`). Tested here: `vidyut.lipi` transliterates IAST ↔ Devanagari ↔ SLP1 correctly (41 schemes);
`vidyut.download_data()` fetches 81 MB (kosha 75 MB). `vidyut.kosha` maps a pada to its morphology
(`PadaEntry.Subanta` with `linga`, `vibhakti`, `vacana` and the stem; `PadaEntry.Tinanta` with `dhatu`, `lakara`,
`purusha`, `vacana`, `prayoga`) and knows classical forms (`bhavati`, `gacchati`, `bhavet`, `kṛtvā`, `dṛṣṭvā`, `śṛṇu`,
`ehi`, `niṣkramyā`), but its keys are pre-sandhi padas in SLP1 (`Darmas` not `DarmaH`, `budDAnAm` not `budDAnAM`),
so every lookup needs a final-sound normaliser, and it knows no hybrid form (`bhaveya`, `lokasmiṃ`, `kṛtvāna`,
`śṛṇohi`, `bodhisattvo`, `ekasmiṃ`: nothing). `vidyut.cheda`, the segmenter, handled a classical frame sentence
except `ekasmin` and the compound `bhikṣusaṃghena` (cut as `bhikṣus am ghena`), and returned nothing at all for the
same sentence with anusvāra finals; its own page calls the module incomplete and recommends the Dharmamitra analyser
instead. `vidyut.sandhi` (a splitter from a rules CSV) and `vidyut.prakriya` (Pāṇinian derivation) are usable
building blocks. Verdict: lipi and kosha are the foundation; segmentation needs more.

### ambuda-org/data

"Data artifacts for ambuda.org": a `dictionaries/` folder of eight XML files (`monier.xml`, `apte.xml`,
`apte_sanskrit_hindi.xml`, `shabdasagara.xml`, `amarakosha.xml`, `vacaspatyam.xml`, `shabdakalpadruma.xml`,
`shabdartha_kaustubha.xml`), `scripts/`, an empty README and no licence file. The XML is the Cologne markup wrapped
in `<entry><key>…</key><value>…</value></entry>`, so these are repackaged Cologne data without Edgerton; Cologne
itself is the source to use.

### Cologne Digital Sanskrit Dictionaries

Forty-four dictionaries, each with a download page (`/scans/<ABBR>Scan/2020/web/webtc/download.html`: text, XML,
DTD, header with the licence) and a git mirror (`sanskrit-lexicon/csl-orig`, `v02/<abbr>/<abbr>.txt`). The ones
that matter here: BHS (Edgerton, 7.6 MB), MW (Monier-Williams 1899, 50.2 MB), AP90 (Apte 1890, 11.8 MB), PWG
(Böhtlingk-Roth, 54.6 MB, German), SCH (Schmidt's Nachträge, German). Headwords are in SLP1 with the printed form
beside them; meanings keep the print's markup; the digitisations are CC BY-NC-SA 3.0 (Sanskrit Library headers) and
the repository CC BY-SA 4.0. The site asks for the citation "(Cologne Digital Sanskrit Dictionaries)" and an
acknowledgement in apps that use the data.

### The Dharmamitra Sanskrit analyser

ByT5-Sanskrit (Nehrdich, Hellwig and Keutzer, EMNLP 2024 Findings, arXiv 2409.13920): one model for segmentation,
lemmatisation and morphosyntactic tagging, trained on the Digital Corpus of Sanskrit. Available three ways: the
hosted API through the PyPI package `dharmamitra-sanskrit-grammar` 0.1.7 (`DharmamitraSanskritProcessor.process_batch(
sentences, mode="unsandhied-lemma-morphosyntax")`), the fine-tuned model `chronbmm/sanskrit5-multitask` on Hugging
Face (T5ForConditionalGeneration, 2.3 GB safetensors, no licence stated), and the inference scripts in
`sebastian-nehrdich/sanskrit-analyzers` ("a GPU is advisable"). It is the best segmenter available for Sanskrit and
the one vidyut defers to; whether it was trained on BHS forms is not stated.

### Texts to test on: GRETIL

GRETIL's TEI corpus (798 Sanskrit texts, plain-text transformations at
`gretil/corpustei/transformations/plaintext/sa_<name>.txt`, each file's header "Distributed under a Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 International License") has the BHS canon Edgerton cites: Mahāvastu,
Lalitavistara, Saddharmapuṇḍarīka, Udānavarga, Mahāparinirvāṇasūtra, Divyāvadāna, Avadānaśataka, the Prātimokṣasūtras
of the Mahāsāṃghika-Lokottaravādins, Sarvāstivādins and Mūlasarvāstivādins, the Bhaiṣajyavastu, Vajracchedikā (with
the Gilgit text), Aṣṭasāhasrikā, Gaṇḍavyūha, Samādhirāja, Kāśyapaparivarta, Suvarṇaprabhāsa, Śālistamba, the
Sukhāvatīvyūhas, Daśabhūmika, Bodhisattvabhūmi and the Pratītyasamutpāda sūtras. The Pāḷi parallels already on the
sites (Udānavarga ↔ Dhammapada, Mahāparinirvāṇa ↔ 7D/3, Prātimokṣa ↔ Vinaya, Śālistamba ↔ the Nidānasaṃyutta) give
ready-made comparison material.

## 3. Design

One new concept, the *language*, selected by `--lang pi|sa` (default `pi`, or detected: a text with `ḥ`, `ṣ`, `ś`,
`ṛ` or Devanagari is Sanskrit). Each language supplies the four Pāḷi-specific parts behind one interface, and the
pipeline, the models and the outputs stay as they are.

1. **Lexicon** (`sanskrit.py`, mirroring `dpd.py`'s `Analysis`/`Headword`): for a form, the candidates with lemma,
   part of speech, parse and meanings. Morphology from vidyut's kosha (after normalising `ḥ`→`s`, `ṃ`→`m`, and the
   pre-sandhi finals); meanings from a SQLite built once by `kavi setup --sanskrit` from Cologne's BHS, MW and AP90
   files (headword in SLP1 and IAST, meanings as cleaned text, the Pāḷi cognate from BHS, the source and page), BHS
   consulted first for a Buddhist text, then MW, then Apte. Compounds: vidyut's kosha already lists krdanta and
   compound members; a splitter over the lexicon fills the gaps as `sandhi.py` does now.
2. **BHS normaliser** (`bhs.py`), the grammar's contribution: a table of hybrid endings and phonological variants
   with the classical form they stand for and Edgerton's paragraph, applied before lookup to produce candidate
   classical forms (`lokasmiṃ` → `loke`, Edg. § 8.63; `bhaveya` → `bhavet`, § 29.28; `kṛtvāna` → `kṛtvā`, § 35.5;
   `-ehi` → `-aiḥ`, § 8.108; `-āna` → `-ānām`, § 8.124; `-o`/`-u` nominative, §§ 8.18–20; `-e` nominative singular
   (the Māgadhism), § 8.25; hiatus bridgers, §§ 4.57–67; `u` for `am`, § 3.58). The analysis then shows the hybrid
   form, its classical reading and the rule, which is what the translator and the reviewer need. The table is built
   from the chapter subdivisions (they are already a list of ending → case/number pairs) and checked against the
   paragraphs' examples; Edgerton's own caution applies, that a form can be read several ways, so the normaliser
   produces ranked candidates, not one answer.
3. **Segmentation**: vidyut's sandhi splitter and kosha for the mechanical cases, the Dharmamitra analyser as an
   optional better segmenter (local through `transformers` on Apple silicon, 2.3 GB, or the hosted API behind a
   flag, since Kavi's promise is to run on the Mac), and the BHS normaliser's candidates in the search.
4. **Glossary, conventions, symbols**: a Sanskrit glossary file seeded from the Pāḷi one through the cognates
   (`dharma` → the Pāḷi `dhamma` line, `skandha` → "collection", `upādāna` → "fuel", `nirvāṇa` left in Sanskrit,
   `bhikṣu` and `Bhagavān` as honorifics), with the author's rulings where Sanskrit terms differ; the textbook
   symbols with the dual `⨁` (already in `grammar.py`) and Sanskrit's extra tenses (`laṭ` ▶️, `laṅ` ↩️, `liṭ` 🔄,
   `luṅ` ⏮, `lṛṭ` ⏭, `loṭ` ⏹, `vidhi-liṅ` ⏯, `lṛṅ` 🔀; `luṭ` and `āśīr-liṅ` need a ruling); the prompts and the
   checker told the language; names, honorifics and terms classified from the lexicon as now.

## 4. Phases and effort

| phase | work | days | gives |
| --- | --- | --- | --- |
| 0 | the author's rulings (symbols, glossary seeds, which dictionaries); `kavi setup --sanskrit` downloads vidyut's data (81 MB) and Cologne's BHS, MW, AP90 and builds `sanskrit.sqlite`; licences in the README | 0.5 | the data in place |
| 1 | `sanskrit.py`: lexicon over kosha + Cologne, final-sound normalisation, compound and sandhi splitting, `kavi analyse --lang sa`; tests on classical prose (Vajracchedikā, Aṣṭasāhasrikā frames) | 2–3 | word tables for classical Sanskrit |
| 2 | `bhs.py` from Edgerton: endings and phonology tables with § citations, ranked candidates, shown in the analysis; tests on Mahāvastu prose and Saddharmapuṇḍarīka verses | 3–4 | word tables for hybrid texts |
| 3 | translation end to end: prompts and reviewer for Sanskrit, the checker's rendering rules, the Sanskrit glossary, interlinear output with the symbols, the Streamlit language switch; the first evaluation sample with a reference (a passage whose Pāḷi parallel the author has translated) | 2 | `kavi translate --lang sa` |
| 4 | optional: the Dharmamitra analyser as segmenter; a chrF harness against published translations where licences allow | 2 | better segmentation on long compounds |

About two to three weeks of focused work; classical Sanskrit translation (phases 0, 1, 3) is about a week, the
hybrid layer (phase 2) the other week. Each phase ends with its tests and a sample in `docs/`.

## 5. Risks and open points

- **Licences**: Kavi is CC0 and ships no data; the DPD (CC BY-NC-SA 4.0), Cologne (CC BY-NC-SA 3.0 / CC BY-SA 4.0),
  GRETIL (CC BY-NC-SA 4.0) and vidyut's data (MIT) are downloaded by `setup`, as the DPD is now, and credited in the
  README and the outputs. The Dharmamitra model states no licence; its API package is usable as is.
- **Coverage**: vidyut's kosha is Pāṇinian, so Buddhist vocabulary (`bodhisattva`, `tathāgata`, `śrāvaka` as
  terms) will often be known only to the Cologne dictionaries, and the hybrid forms only through the normaliser;
  Edgerton's dictionary cites forms by text and page, which lets the normaliser be checked against the corpus.
- **Segmentation** is the weak point of every Sanskrit tool; long compounds and verse sandhi will need the
  Dharmamitra analyser or the author's eye.
- **Rulings wanted from the author**: the Sanskrit glossary (does `dharma` follow the Pāḷi "Dhamma"? names in
  Sanskrit or Pāḷi form, `Śāriputra`/`Sāriputta`?), the symbols for the dual and the two extra tenses, whether
  technical terms are shown in the text's own form (`dharmaḥ` (the Dharma)), and which texts to test on first.

## 6. Implementation status (2026-11-03)

Phases 0, 1, 3 and the systematic part of 2 are in place; the author's rulings were: replicate the Pāḷi glossary as
far as the cognates allow, names stay in Sanskrit; new symbols from Unicode for the forms Pāḷi lacks; technical terms
in the text's own form; test against the author's Heart and Diamond Sūtra pages on buddhavacana and correct their
mistakes.

- **Data** (`kavi setup --sanskrit`, `kavi doctor --lang sa`): vidyut's data in `data/vidyut/`, Cologne's `bhs.txt`,
  `mw.txt`, `ap90.txt` in `data/cologne/`, built into `data/sanskrit.sqlite` (339,000 entries, 70 MB) by
  `src/kavi/cologne.py`: markup stripped, Sanskrit in IAST, Edgerton's Pāḷi cognates kept, `{{Lbody=N}}` cross-
  references resolved; the lookup puts the common word before the proper name (Edgerton capitalises a name's
  headword, Monier-Williams says `N. of`), reads a nasal both ways (`saṅgati`, `saṃgati`), and gives the genders
  (`gambhīra mfn.`, `lakṣaṇa n.`; Edgerton's first), the weight of an entry (a proxy for how common the word is) and
  whether a headword is only a root or a letter.
- **Lexicon** (`src/kavi/sanskrit.py`, the `DPD` interface: `analyse`, `known`, `deconstruct`): the kosha's parses
  with DPD-style parts of speech and parse strings, the lemma as the author writes it (stem, third-singular present
  verb, participle with its verb, `aham`/`tvam`), participles and absolutives with their affixes, primary nouns made
  by kṛt affixes as plain nouns, the kosha's spurious genders filtered by the dictionaries' (a-stems exempt as the
  last member of a compound), parses ordered own gender, singular, nominative first; a regular inflection read on a
  model stem for a dictionary word the kosha lacks (`tathāgatasya`, taddhita adjectives such as `paścimika`, the
  feminine of an adjective); compounds split into dictionary members with the junction variants (`cittāvaraṇa`,
  an-stems, numerals, the cvi `ī`), Monier-Williams' own member marks (`sva—bhāva`, `a-mala`), negation shown as
  `na + X` except for a term (`avidyā`), `-tva`/`-tā` set apart, prefixes rejoined, an epithet and a name kept as one
  name (`āryāvalokiteśvara`); words joined by sandhi split (`nāvidyā`, `śūnyataiva`, `tathāgatāyārhate`, chains)
  and weighed against a compound reading by the quality of what each is made of; the indefinite pronoun
  (`kaścit`); `INDECLINABLES` and `PARTICLES` for the function words vidyut inflects.
- **Hybrid forms** (`src/kavi/bhs.py`): 48 rules from Edgerton with their paragraph numbers, applied only when a
  form is not otherwise known and reported in the analysis (`read as bodhisattvo (Edg. § 2.84 …)`); a hybrid
  spelling of a compound or of words run together is read through the same rules.
- **The Diamond Sūtra's lessons** (the second pass, 2026-11-02): a finite verb or participle the kosha knows only
  without its prefixes is read by taking the prefixes off as they stand in the word and putting them back on the
  lemma (`samanupaśyati`, `paryavāpnuyāt` = pary + av + āpnoti, `udgrahīṣyanti`, with the hybrid spellings of the
  rest: `udgṛhīṣyaṃti` by § 31.10, `adhimucyāmi` by § 37.22, `bhāṣet` by § 37.10); an honorific or a name is a noun,
  never the participle or the avyaya vidyut derives it from (`arhat`, `sugata`, `bhagavan`); a Buddhist name is what
  Edgerton lists only as a name, or what the dictionaries know only as a name (`Subhūti` masculine before the
  adjective `subhūta`, `Anāthapiṇḍada` whole, `Śākyamuni`), and Monier-Williams' name entry gives its gender; the
  strong forms of `mahat` and the perfect `āha` (as the author writes it) are supplied; `sa`, `caitya`, `anāgāmina`
  before a vowel are read with the visarga that dropped, `ta`/`ya`/`ka` with the `e` that became `a`; a form reached
  as written ranks before one reached through a sandhi variant (`mahān` is `mahat`, not `maha` read with `-t`);
  `yāvat` is the adjective unless spelt as the particle, and `kāle`, `antikāt`, `sārdham`, `sacet` are placed by
  their kind; a compound's members are the dictionary words (`sattva`, not the kosha's `satvan`; `tatas`, not
  `tato-`), its feminine last member keeps its `ā` (`satvasaṃjñā`), a verbal prefix is never a member (`saṃbahula`,
  `anuparindanā`), and a negation of a well-known word beats two chance words joined by sandhi (`adhātuḥ`); a
  hiatus-bridging consonant written with hyphens (`vidikṣu-r-avidikṣu`, §§ 4.59–65) splits the two words; an
  absolutive of a compound verb shows its members (`🔽(tvā)🆎(tri+pradakṣiṇa+karoti)`); the interlinear cache key
  carries the candidate parses, so a lexicon change re-asks only the sentences it changed. From the Gilgit
  sections: `ś` written `cch` after `ṃ` (`cchrutvā`), a visarga written `s` before `t` (`bahavas tāsu`), the sandhi
  finals of a verb (`anuprāpnuyuś`, `paryavāpnuyād`), Monier-Williams' `mf(vī or u)n.` as an adjective (`bahu`),
  `śrad` as a prefix, a sandhi split led by an absolutive (`śrutvā + abhiśraddadhāsyanti`) before a compound of
  scraps, and a reading only a hybrid rule gives, of a stem the dictionaries lack, counted as nothing when the
  word splits into words that stand on their own. The lint's glossary alternatives now match whole lemmas and
  compound members only (`bhava`'s "being" had been turning every "being" of a sentence into "existence").
- **Absolutives** are the readings the kosha is weakest on: vidyut lists them as avyaya doubles (`āśritya` as an
  indeclinable beside the kṛdanta), lacks the causatives' (`praṇāmya`, `vivarjayitvā`) and some prefixed verbs'
  (`abhivandya`), and Monier-Williams calls the form `ind.p.`; kavi drops the double, derives the missing ones from
  the finite verb it does know (`praṇamati`, `vandate` with the prefix put back) and ranks a prefixed verb's
  `-ya` absolutive as the usual reading.
- **Pipeline**: `--lang sa` on every command (`kavi app` has a Pāḷi/Sanskrit switch); `src/kavi/language.py` carries the language record that the
  interlinear, the prompts, the glossary (terms and honorifics in stem form, `Bhagavān`) and the tokeniser read
  (hyphenated compounds one token, the avagraha restored, `‘` as well as `’`); `grammar.py` and `dpd.py` know the
  dual ⨁, the periphrastic future ⏩ and the benedictive ⏫; `glossaries/sanskrit.txt` carries the Pāḷi glossary's
  renderings to the cognates and the Prajñāpāramitā vocabulary.
- **Test**: the Heart Sūtra (the author's Interlinear tab, 125 tokens): after four passes the analysis line agrees
  on 104 tokens; the rest are the model's parse choices (adjectives in `-ā` read as feminine singular where the
  noun is masculine plural, `rūpān` accusative for ablative) and three conventions where kavi is the more
  consistent (`🔽(ta)` on every past participle, `nāsti` + `🔽(tva)`); `niṣṭhanirvāṇa` is read `niṣṭha + nirvāṇa`
  where the author reads `niṣṭhā`. The Diamond Sūtra (Schøyen MS2385, sixteen sections, 338 units, 2,211 tokens)
  took two passes (the second re-asked the 269 units whose candidates the lexicon fixes had changed, the rest came
  from the migrated cache) and left one word unread (the s-aorist `acchetsīn`) and about sixty tokens to correct
  by hand (`scratchpad/postfix_diamond.py` on the buddhavacana side: the model's vocatives for nominatives, two
  words cut where one stood or joined where two stood, the forms in `-tamām` written `-sṛtamām`, the glosses the
  model left as dictionary text, and the house renderings Bhagavān, Sugata, Samyaksaṃbuddha, āyuṣmān in the
  translation lines); the result is the Interlinear tab of each section of the author's page. The Gilgit sections
  of the same page (§§5, §§7–§§12: 149 units, 1,774 tokens, 62 minutes) followed the same path with their own
  table of about seventy hand fixes (`postfix_gilgit.py`); of their thirteen unread words six are the edition's
  lacuna marks and fragments, the rest the manuscript's own slips (`buddabodhiṃ`, `dharmaḥsa`) and sandhi
  spellings the lexicon has since learnt (`cchrutvā`, `bahavas`, `anuprāpnuyuś`, `paryavāpnuyād`). The page now
  carries an Interlinear tab in all twenty-three sections that have Sanskrit, and builds clean.
- **The Mūlamadhyamakakārikā's lessons** (2026-11-03, Nāgārjuna's 449 verses from the DSBC text, for a page of
  buddhavacana with a Translation, Sanskrit and Interlinear tab per chapter): a negated word the dictionaries have
  only unnegated (`anirodha`, `anirgama`, `anānārtha`) is read on the model stems as na + the word they know, with
  the kosha's own derivation kept (`amithyātva` = na + mithyā + tva) and the base word's gender; both readings of a
  word in `an-` are tried (`a + nirodha`, not `an + irodha`) and decided without a full analysis; a chain of such
  words splits (the maṅgala's `anirodham anutpādam anucchedam aśāśvatam` and its second line); among the sandhi
  splits of a word, one whose parts are all words, or sound compounds of known words (`na + avidyākṣayo`), wins
  over one with a scrap, and then the fewer parts (`nāpyahetutaḥ` = na + api + ahetutaḥ, the table's `nāpi`
  opened out; `tathāgatāya + arhate` over a three-member compound of the same quality); a split at a consonant
  (`parān + ugrāhakaṃ`) never admits a pronoun followed by a compound reading, since that is what every compound
  looks like; a three-letter part must be the word itself (`īni` is not the particle `ī`); `nā-` before a consonant
  with no direct reading is na + a- (`nānyat`, `nārhati`, `nāpratyayavatī`); a name in the vocative is never
  penalised (`Subhūte`), a feminine ā-stem read only as a vocative or a dual is (`vande` is the verb); `dve` and
  `ubhe` are duals only, `ādīni` is `ādi` (the kosha has only `ādin` "eating"), a taddhita in `-vat`, `-mat`,
  `-vin`, `-min` on an ī-feminine is the adjective (`pratyayavatī`) and never a chance name. A recursion
  (`_resolve → _by_model → _make_noun → _expand_members → _compound_splits → _resolve`) is cut by a guard. The
  DSBC's own slips (`kecanaḥ`, `ārambaṇam` for `ālambanam`, a doubled `r`, a lost anusvāra) stay unread, as they should.
- **The Mūlamadhyamakakārikā's second lesson: the consonant junctions and the ranking of splits** (2026-11-03, after the
  first full run left 122 tokens unread and skipped three verses as "not Sanskrit"; settled over five scans of all 2,096
  distinct tokens of the text with `scratchpad/mmk/scan_all.py`, each scan read for junk chains, and the 110 unread forms
  probed after every change). The DSBC writes the sandhi of a word's final consonant with the next word's initial inside
  one token, and `_sandhi_splits` now cuts those junctions too: a visarga written `r` before a voiced consonant after `i`,
  `u`, `e`, `o`, `ṛ`, `ai` (`siddhir na`, `hetur jāyate`, `anayor na`, `tair gatiṃ`; never after `a` or `ā`, so `svapaḥ +
  ātmānau` is no reading), `cc`/`cch`/`jj`/`dd`/`ddh`/`nn`/`nm`/`ll`/`ṃst`/`ṃśc`/`ñj` for a final `t`, `d` or `n` (`tac ca`,
  `tasmāc chubham`, `syāj jāyate`, `kecid dhi`, `yan na`, `imāl lokaḥ`, `tāṃs tān`, `skandhāṃś ca`, `yāñ janāḥ`), `g` for a
  final `k` (`vāg viṣpandaḥ`), `ṭ` written `ḍ` (`ṣaḍ eteṣāṃ`), `ar` for `a + ṛ` (`tathā ṛṇam`), `o` for `a + ū`
  (`cordhvam`), `āv`/`āy` before a vowel for `au`/`ai` (`ubhāv utpādayet`), a final `n` doubled before a vowel (`bhajyerann
  utpadyeran`), a `y` or `v` junction only after a consonant (`pratyai` is no word), an avagraha dropped after `ca`
  (`casau`), a verb's final `e` written `a` before a vowel (`utpadyata ime`), `datvā` for `dattvā`; `cet`, `vinā`, `ṛte`,
  `tridhā`, `āho`, `sat`, `asat`, `ṣaṭ`, `ādi`, `abhūm` and the first-person middle endings (`prajñapayemahi`) are known,
  `moha` is masculine whatever the dictionary says, and the hand-listed nominals come before the kosha's chance verbs
  (`asat` is not an imperfect of `sas`). A chain may hold an inflected compound as a part (`cittasaṃtānaḥ + cetasaḥ`,
  `syāt + apradīpanahetukaḥ`, `vyayasya + apunarutpatteḥ + hetūcchedaḥ`) when it is sound on its member surfaces
  (`_good_info`: two to four members, none a scrap under four letters, none ending in a visarga or its `s` before `t`/`c`,
  none beginning like no word, the last a nominal (an `-ādi`, a bare `i`/`u` stem, `prabhṛti` count) and no pronoun
  proper or finite verb, a feminine `-ā` only where the dictionaries allow it, no bare negation of a plain word and no
  negation before a prefix, no absolutive member (`apekṣya + agniḥ`) unless it is also an adjective of an uncommon verb
  (`ananya`) or `pratītya` before `samutpāda`, no inflected pronoun member (`iyam + ātmānam`), every member weighed as
  written with its own compound reading and a negation's base counting (`upādāna`, not `upā + dāna`; `parātmānau` =
  para + ātman; `ananya` as `anya`), and a compound the dictionaries list (`jarāmaraṇa`, `pratītyasamutpāda`) counting
  as one piece), and chains may be eight words long (`nābhūm atītam adhvānam ity etan nopapadyate`). The remainder of a
  junction is tried both as one word and as a chain, and the ranking decides, in this order and no other (every other
  order tried let chains of chance words beat sound compounds or the reverse): every part a word; the fewest chance
  readings (a noun no dictionary weighs, a hybrid reading, a form modelled on a stem only vidyut lists, a chance verb: a
  rare tense or an imperative of an uncommon verb, or a first or second person or dual of one with no meaning; an
  avagraha-less `aḥ + a` junction counts as one, since the text writes its avagrahas; a vocative alone is no word); the
  fewest pieces with a particle counting half (`tāvat + na + apratyayāḥ` before `tau + annāpratyayāḥ`, `tasmāt + na +
  atra` before `tasmāt + nātrā`); the most particles (indeclinables and the hand-listed verb forms); the fewest parts; a
  negation before its `ā-` twin (`abhāvaḥ`, `asthitaḥ`); the strongest words (a particle, pronoun or verb of a common verb
  before a noun; `apekṣya` before `apekṣyā`, `tayā` before `taya`); the dictionaries' weights (a verb form by its verb,
  ten if common, else three, never by its suffix `māna`); a short initial vowel last. A negated absolutive or participle
  the dictionaries lack is one word (`abhūtvā`, `anupādāya`, `ajanitaḥ`, `anupālabdhaṃ`), read ahead of a dative of a
  stem vidyut invents (`anupāda`) and of a participle of a verb that does not exist (`apaśyati`); a double negation is
  none (`an + asādhya`); `a + tmānam` is not a + the Vedic `tman`; a negation's base may be a term of the text whatever
  its weight (`agantā`), takes any gender when the dictionaries call it an adjective too (`gantṛ`), and a compound in
  `-a` may be a bahuvrīhi in any gender (`anupādāno`); the `-tva`/`-tā` abstracts are modelled (`anyatvam`,
  `nirapekṣatvāt` neuter, `ahetukatā` = na + hetuka + tā); a participle of a prefixed verb the kosha lacks is read like
  its finite forms (`anuvarṇitām`, `abhirūḍhaḥ`, `upādattam`), also when the direct readings are only chance verbs; the
  common-verb list carries the verbs of the argument (`apekṣate`, `upapadyate`, `prasajyate`, `nirvāti`, `pratyeti` …) and
  is consulted behind a negation (`anapekṣate`); a sure split (particle or pronoun first) is taken only when it is also
  the best-ranked; in the pair-versus-compound rule a compound's quality is measured on its surfaces, a pair of modelled
  or hybrid words is not plain, a negated known word stays whole, and a pair that merely cuts the compound loses to it
  (`prajñāpāramitā + caryāṃ`). `KAVI_DEBUG_SPLITS=1` prints every candidate split with its score and each part's reading,
  and the pair-versus-compound decision. What remains wrong is what only the sense decides (`nāsi ādiḥ` for `na asya
  ādiḥ`, `tat śeṣamuktaṃ` for `tat śeṣam uktaṃ`, `sannāsanna`) and goes into the page's postfix table with the DSBC's
  slips and the one-letter preposition `ā` (`tiṣṭhaty ā pākakālāt`).
- **The Mūlamadhyamakakārikā's third lesson: the function words and the dictionary's hyphenation** (2026-11-03, after
  the full interlinear run of the 449 verses was read token by token): `kutaḥ` read as a name (`kuta` masc nom sg, 34
  times), `tataḥ` as `tata`, `kathaṃ` as the accusative of Edgerton's `katha`, `saḥ` as the prefix `sa-`, `sati` as a
  hybrid vocative, `asati` as a present of `as` "throw", `asti` as Edgerton's asseverative particle, `janayate` as the
  vocative of a feminine `janayati`, `dharma utpadyate` with `dharma` only a vocative, `prahāṇa` as `prahā + ṇa`,
  `upādāna` as `upā + dāna`, `svarga` as `svar + ga`, `nanu` as `na + nu`, `atra` as `na + tra`, `vikalpataḥ` as `vikalpa
  + ta`, `tiraskṛtya` as a gerundive of `tiraskṛṇatti`. The causes and the rules: the `PARTICLES` filter keeps an
  indeclinable only when its stem is spelt as `INDECLINABLES` spells it, so the kosha's `kutas` fell to the filter made
  for `kutaḥ` — the table now carries the kosha's spelling (`kutas`, `tatas`) and the common adverbs a nominal homonym
  shadows under the pronoun-before-particle rule (`katham`, `kutra`, `yatra`, `anyatra`, `paratra`, `sarvatra`, `ekatra`,
  `sarvadā`, `ekadā`, `kadā`, `nanu`, `prāk`, `jātu`, `kvacit`, `kvacana`, `kuha`, `anyathā`, `uta`, `mithyā`, `svayam`);
  `ceti`, `yacca`, `tacca`, `athāpi`, `cāsau`, `nātra`, `yāvanna`, `tāvanna` are `SANDHI_PAIRS`; a bare `-a` before a vowel
  is judged on its own stem's entries (`dharma` is only a vocative of `dharma`, whatever `dharman`'s neuter forms say), so
  the nominative with its visarga lost is read, and the indeclinable the `-a` may be (`kuta eva`) — such a reading is
  marked in its grammar and counts for nothing as a non-final part of a split, since a visarga-lost word stands before
  a space and is never joined to the next word (`rūpe 'satyeva` is `asati + eva`, not `asatya + eva`; `anavasthaivaṃ`
  keeps `anavasthā`); `anyathā` and `mithyā` are not particles of the table, being members of `anyathābhāva`,
  `mithyādṛṣṭi`; the hybrid vocative in
  `-i` (Edg. § 10.33) comes after the verbs, pronouns and participles (`sati` is the participle `sat`; `bodhi` keeps the
  vocative first); a word of the common-verb list is the verb, not an avyaya spelt alike (`asti`); the kosha's nominal
  entries for the prefixes `sa-`, `su-`, `dus-`, `ku-` are no words (`PREFIX_ONLY`); a stem that is itself a finite verb
  form is not a nominal stem, in `_direct` and `_by_model` (`janayate`), and the verb-ending readings of Edgerton's
  chapters 25–37 are tried when no finite verb reads (`janayate` = `janayati` with the middle ending, §§ 37.24–25) — beside
  other readings only the voice rules and only a common verb (not `mahate` as `mahati`, not `sati` as `santi`); an adverb
  in `-tas` on a known stem is read (`vikalpatas`, `dhātutas`, tasil); a negated participle of a common verb ranks with
  the verbs (`asati` = na + sat of `asti` before the chance present), and a present of a verb outside the common list is no
  anchor in a split (`hetau + asati`, not `hetā + āvasati`); Monier-Williams' members are shown only when each is a word
  of three letters or more with a weight (`svar—ga`, `taj—ja`, `prahā—ṇa`, `upā-dāna`, `pañca—dhā`, `niś—caya` are one
  word; `SUFFIX_PARTS` has `dhā`, `śas`, `dā`, `tra`; `PREFIX_SANDHI` the prefixes as MW writes them before a member); an
  absolutive on a root the kosha cites by another present is read through `ABSOLUTIVE_ROOTS` (`tiras-kṛtya`: `karoti`);
  an adverb in `-tas` or a particle is no compound member (`sa + nipa + atas + tri`). What the review still had to fix by
  hand, for the lexicon's next round: a `-tā` agent noun read as a periphrastic future (`gantā`, `kartā`, `bhoktā`),
  `kiṃcit` as a noun, `kasya` as `ka`, `parakṛtam` as `parakṛti`, `tad eva` as `tadā + iva`, the ātmanepada past tenses
  marked active, a neuter accusative given as nominative, `hetoḥ` as an ablative, the one-place shift of the model's
  glosses after a token it could not read, the `-m` junction inside a word the chain splitter cuts into scraps
  (`utpādotpādam utpādo`, `kriyādīnām asaṃbhave`, `sadbhāvam anupaśyasi`), and a compound reading that stands beside the
  right pair for the model to choose (`asatyalakṣaṇe`: `na + satya + lakṣaṇa` beside `asati + alakṣaṇe`, the locative
  absolute); `athāpyanantavāllokaḥ` still reads in isolation and not in the full scan (an order-dependent cache).
- **Pāṇinian rules and Ambuda DCS frequencies** (`src/kavi/panini.py`, 2026-11-11): codifies Pāṇini's *Aṣṭādhyāyī*
  morphophonemic and derivational rules alongside Kaccāyana's *Sandhikappa* and Edgerton's *BHSG* — external *ac*,
  *hal* and *visarga/rutva* sandhi (including 8.3.14 ``ro ri`` + 6.3.111 ``ḍhralope pūrvasya dīrgho 'ṇaḥ`` and 8.3.36–37
  ``vā śari`` / ``kupvoḥ``), internal *ṇatva* (8.4.1–14) and *ṣatva* (8.3.59) across prefix and compound boundaries,
  *cvi* stems before ``kṛ``/``bhū`` (5.4.50), *samāsānta* stem alternations (5.4.68–154), *taddhita* initial *vṛddhi*
  reversal (7.2.117), and ``-tṛ`` agent nouns (3.1.133 & 4.1.5 vs 4.1.10 ``na ṣvasrādibhyaḥ``, so ``kartā``, ``gantā``
  and ``bhoktā`` rank as masculine nominative singular agent nouns ahead of the periphrastic future). Incorporates
  attested Buddhist Sanskrit compound-member and lemma frequency sets from Śāntideva's *Bodhicaryāvatāra* and
  Aśvaghoṣa's *Saundarananda* in ``ambuda-org/dcs`` (CC-BY 4.0); extends model-stem ending length to seven characters
  (``-ebhyaḥ``, ``-ībhyaḥ``, ``-ābhyām``), filters root-only and single-letter entries out of nominal and compound
  member checks, and resolves ``kiṃcit``, ``kasya``, ``parakṛtam``, ``tad eva`` and ``utpādotpādam utpādo``.
- **Still open**: the rest of Edgerton's tables (verbs of chapters 25–43, the pronoun and numeral chapters) as
  rules; the Dharmamitra analyser as an alternative segmenter; an evaluation harness; the kosha's junk stems
  (`vastum` as a masculine, `rūp`) are suppressed by rank, not removed.

## Sources

Edgerton's grammar as converted in `buddhism-texts/markdown/Sanskrit/`; the Cologne download page for BHS
(`https://www.sanskrit-lexicon.uni-koeln.de/scans/BHSScan/2020/web/webtc/download.html`) and `bhs-meta2.txt`,
`bhsheader.xml` in `github.com/sanskrit-lexicon/csl-orig`; `https://gandhari.org/dictionary?section=bhsd` and its
`dictionary.js`; `github.com/ambuda-org/vidyut`, `vidyut.readthedocs.io`, PyPI `vidyut` 0.4.0;
`github.com/ambuda-org/data`; `https://www.sanskrit-lexicon.uni-koeln.de/`; `huggingface.co/buddhist-nlp/mitra-qwen35-translate`;
`arxiv.org/abs/2409.13920`, PyPI `dharmamitra-sanskrit-grammar`, `github.com/sebastian-nehrdich/sanskrit-analyzers`,
`huggingface.co/chronbmm/sanskrit5-multitask`; `gretil.sub.uni-goettingen.de`.
