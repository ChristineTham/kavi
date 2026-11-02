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

## 6. Implementation status (2026-11-02)

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
