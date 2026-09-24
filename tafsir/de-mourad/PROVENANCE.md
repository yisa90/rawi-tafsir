# de-mourad — provenance, rights, and honest coverage

## Edition

**Erläuterung des Koran (Tafsīr)** — 12 volumes, complete, suras 1–114
Samir Mourad (with Samir Basyouni and Neimet Nabil on individual volumes)
Deutscher Informationsdienst über den Islam (DIdI) e.V., Heidelberg / Karlsruhe
First published 2013–2020. **This extraction reads the current print-ready
revisions, not the first editions** — Band 1 is the 4th edition (October 2023),
and the volumes range from Band 9's 3rd edition (October 2022) to Band 1's and
Band 2's of October 2023. Samir Mourad signs each revision as a full re-read and
correction (*"Gesamtdurchsicht und Korrektur"*).

It is *tafsīr bi-l-maʾthūr* — transmitted commentary, drawn from aṭ-Ṭabarī, Ibn
Kathīr, and in the last two volumes az-Zuḥailī's *Tafsīr al-Munīr*.

## Source — the publisher's own Word files, not the public PDFs

DIdI publishes, for every volume, the **print-ready `.docx` source** alongside
the PDF, at <https://www.didi-info.de/tafsirdateien> under the downloads category
`3-quelldateien`. All twelve were fetched from there on 2026-09-24, each `HTTP
200`, each a real Word document inside a ZIP that also carries the Othmany
Qur'anic fonts the print edition uses.

**This is the single most important fact about this extraction.** Reading the
Word source instead of the PDFs removes, structurally rather than heuristically,
the two defect classes that dominated the Rassoul extraction:

- **no page breaks**, so no commentary paragraph is ever split in two — the
  defect that truncated 465 Rassoul records; and
- **no running headers or page numbers in the text stream at all** — they live in
  `word/headerN.xml`, which the extractor never opens.

Band 12 (suras 67–114, ISBN 978-3-940871-22-0) is **not** listed on DIdI's
`downloads/category/2-buecher` page, which is where earlier research looked for
it and failed. It is listed on `/tafsirdateien`, as `Band 12`, in both `.docx`
and `.pdf`. The volume in hand is the 3rd edition, April 2023.

Volume → surah map, read from the twelve files themselves. The `Heading1` count
across the twelve is **exactly 114**, which is the completeness proof:

| Band | Suras | Band | Suras |
|---|---|---|---|
| 1 | 1–2 | 7 | 19–23 |
| 2 | 3–4 | 8 | 24–29 |
| 3 | 5–6 | 9 | 30–37 |
| 4 | 7–9 | 10 | 38–49 |
| 5 | 10–13 | 11 | 50–66 |
| 6 | 14–18 | 12 | 67–114 |

## Rights — a waqf with a named approval channel, NOT a blanket licence

Printed on the title page of every volume:

> Die Rechte am Text dieses Buchs sind ein Waqf, eine islamische Stiftung. Die
> Verwaltung des Waqf erfolgt ausschließlich durch den Deutschen
> Informationsdienst über den Islam e.V. Im Rahmen seiner Verwaltungsaufgaben
> behält sich der Deutsche Informationsdienst über den Islam e.V. das Recht der
> Genehmigung von Übersetzungen oder Nachdrucken des vorliegenden Textes oder von
> Teilen davon vor.

The text rights are an Islamic endowment administered solely by DIdI, and DIdI
**reserves the right to approve** reprints. This is **not** Rassoul's printed
blanket permission. It names a door; it does not open it.

⚠️ **The attribution string currently in `editions.json` is a PROVISIONAL
PLACEHOLDER written by this extraction, not wording DIdI has approved.** It is
deliberately phrased so it cannot be mistaken for approved text. The founder is
handling the rights conversation with DIdI directly; the exact required wording
comes from them and replaces the placeholder before this edition ships.

The edition is gated behind `awaiting_scholarly_review: true` (ADR-013), so
nothing reaches a user while the rights answer and the scholar of record are both
outstanding.

**One thing this edition makes cheaper:** Mourad states in his own methodology
that his German ayah renderings are mostly taken from Rassoul — *"Die deutsche
Koranübersetzung ist meistens von der von Muhammad Rassoul übernommen"* — and
Rawi holds a printed reproduction licence for those. But Rawi does not ship his
renderings at all (see below), so this affects the rights conversation, not this
data.

## What a record contains

**Commentary only.** Mourad's own German renderings of the ayahs are excluded —
**5,969 rendering paragraphs, 934,794 characters.** Both apps render a verified
German translation (Bubenheim & Elyas) directly above the tafsir, and a second,
unverified rendering must not appear underneath it unlabelled.

A record carries, in print order: the section title (the range marker stripped),
the sub-section headings, and the commentary prose. Surah introductions, which
belong to no single ayah, ride on the ayah-1 record — the convention the English
Ibn Kathir edition in this same dataset already uses.

**2,934 pure-Arabic paragraphs are excluded.** These are the isnād chains Mourad
prints before his German translation of each narration. They are untranslated
source apparatus, they would render RTL inside an LTR block, and the German
rendering that follows each one is self-contained. `--keep-arabic` reverses this;
it is a display decision and it is recorded here rather than made silently.

**319 print hyphens were rejoined** (`Auf-erstehung` → `Auferstehung`). The Word
files bake print hyphenation in as ordinary hyphens — there is not one soft
hyphen in the twelve volumes — so these would have shipped as-is. A hyphen is
removed only when the two halves joined form a word that occurs elsewhere in
these same twelve volumes unhyphenated. That is why the Arabic transliterations
(`al-khauf`, `an-nubuwwa`, `Ahlul-kitab`) and the German compounds
(`Meister-Schüler-Beziehung`) keep their hyphens: `alkhauf` never occurs.

## The rendering exclusion — how it is enforced, and what is left open

Mourad prints his renderings in a block under each section heading, and then
often **re-prints the same ayahs** under a later sub-heading as the passage then
under discussion. Both copies must go. Three passes do it:

1. **The rendering run.** The paragraphs immediately following a block-opening
   heading that end with an ayah reference for that surah. The run stops at the
   first paragraph that is not one, so commentary is never swallowed. The basmala
   is skipped *without* stopping the run — stopping there would leak every
   rendering in the surah.
2. **Ascending groups.** After commentary has begun, a run of two or more
   consecutive ref-terminated paragraphs with **distinct ascending** ayah numbers
   is a re-print (370 paragraphs). A run that repeats **one** ayah is a lemma
   sequence — the ayat al-kursijj commentary quotes `[2:255]` ten times, each
   followed by its gloss — and lemmas stay, because a phrase quoted inside
   commentary is intrinsic to it.
3. **Content match.** Every paragraph the run already identified as a rendering
   is known text, so any paragraph anywhere in the corpus that reproduces one is
   the same rendering a second time and is removed: **1,528 of them.** This is
   exact rather than heuristic, and it is what makes the rule a guarantee. No
   record was emptied by it, so no commentary was lost. The index is built from
   *both* exclusion sets: from the runs alone it missed 41 paragraphs that appear
   a third time, which is the kind of hole only a check outside the parser finds.

**Verified independently of the parser.** Re-reading the written corpus and the
audit file afterwards, the number of excluded renderings that reappear anywhere in
their own surah is **0**. That check does not trust the extractor's own
bookkeeping, and it is the one to re-run after any change to these rules.

### ⚑ Still open — 78 paragraphs, listed not guessed

`EXCLUDED-RENDERINGS.txt` in this directory is the full audit: every paragraph
removed, and every paragraph kept-but-flagged, with its block key.

**78 paragraphs remain that are ref-terminated, of full-ayah length, for an ayah
inside their own block, and carry no attribution word.** They are **kept**, not
dropped, and flagged for a native German reviewer. They are genuinely ambiguous:
some are commentary that happens to close on a citation (`Scheich Azzindani:
Prof. Siaveda erläuterte uns, …`), some are a full ayah standing as the anchor
for the gloss in the next paragraph. Rules cannot separate those two, and the
safe direction for *coverage* and the safe direction for *scripture* point
opposite ways here. **This is the review's call, and it is the one place this
extraction defers.**

Also recorded, and kept on the Rassoul precedent that a quotation inside
commentary belongs to it: **980 quotations of a different ayah** than the record's
own (a numbered rendering of `[38:71-86]` appears inside surah 2's commentary as
evidence). These are still Mourad's unverified renderings. If the review wants
them gone, that is a rule change, not a bug fix.

## Coverage — 6,213 of 6,236 ayahs (99.63%)

Commentary blocks: **1,505.** Ayahs carrying commentary: **6,213.** Ayahs whose
text comes from more than one block (overlapping ranges, e.g. `[67:12-14]`
followed by `[67:13-15]`): **233**; both blocks are kept and concatenated in
print order.

**The 23 missing ayahs are gaps in the printed book, not extraction failures.**
The heading sequence simply skips them — surah 19 runs `[19:38-40]` then
`[19:51-53]`:

```
14:52   19:41-50, 56   21:10   22:30-33   38:40   48:4, 24-26   98:6
```

Of those 23, **14 have commentary that exists but that the book never keyed**:
six sections carry no range marker at all, and their content stays attached to
the block above rather than being keyed by inference. Guessing a key would move
commentary onto ayahs the author never assigned it to, so the intervals are
reported instead:

| Section | Would occupy |
|---|---|
| Geforderte Charaktereigenschaften | 17:22–? |
| Abraham, Isaak und Jakob (Friede sei mit ihnen allen) | 19:41–50 |
| In der Annahme der Botschaft des Koran liegt die Ehre eines Volkes | 21:10 |
| Standhaftigkeit der Mu'minūn | 46:15–? |
| Allah verhinderte Blutvergießen bei Hudaibija … | 48:24–26 |
| Das Streben nach Ansehen unter den Menschen … | 107:8–? |

The remaining 9 (`14:52`, `19:56`, `22:30-33`, `38:40`, `48:4`, `98:6`) are
genuine silences in the book.

### One source erratum, repaired and listed

`[20:115-227]` — surah 20 has 135 ayahs, so `227` is not an ayah. The next
heading is `[20:128]` and this is the last section before it, so it reads as
**`[20:115-127]`**. Only the ayah keying is touched; the commentary text is
untouched. Left unrepaired this was the largest hole in the corpus, 13 ayahs.
It is the only out-of-range heading in 1,508, and after the repair none remains.

### 21 block ranges were widened past their heading

Some headings understate what is printed under them: the block titled
`[2:153-154]` prints renderings through `[2:157]`. The rendering run is allowed
to continue past the heading's upper bound while the ayah numbers keep ascending,
and the block is then extended to what was actually rendered. Left alone this
both leaked the 2:155–157 renderings into commentary and opened a three-ayah
hole — one rule closed both.

## Size — and why the fan-out number is not the bundle number

Range commentary is replicated onto every ayah in its range, as
`convert-qul-tafsir.sh` already does for fr/tr.

| | |
|---|---|
| Records | 6,213 |
| Total text | **26.54 MB** |
| Distinct texts | 1,593 |
| Distinct text | **5.21 MB** (19.6%) |
| Replication | **5.10×** |

**Only a fifth of this edition's bytes are distinct.** The `.rtb` bundle format
dedupes identical text across ayahs, so the shipped bundle pays roughly the 5.21
MB, not the 26.54 MB — comparable to Rassoul's 5.05 MB. The 26.54 MB is paid by
**this git tree**, and by anything that still reads the per-ayah CDN path.

Record sizes are lopsided by the same mechanism: **265 records exceed 20 KB and 2
exceed 50 KB**, the largest being `36:1` at 98 KB (Ya-Sin's 32-ayah opening block
plus the surah introduction). p50 is 2,380 characters.

## The range question — reported here, decided by eng-lead

Mourad keys commentary to ayah **ranges**, which is the structural difference
from Rassoul. 1,505 blocks:

| Block size | Count | Block size | Count |
|---|---|---|---|
| 1 ayah | 329 | 11–15 ayahs | 54 |
| 2 ayahs | 323 | 16–20 ayahs | 33 |
| 3 ayahs | 247 | 21–30 ayahs | 13 |
| 4 ayahs | 163 | 31–59 ayahs | 5 |
| 5–10 ayahs | 339 | | |

**Only 329 of 1,505 blocks (21.9%) are single-ayah.** The median block is 3
ayahs. The largest are `26:10-68` (59 ayahs), `28:1-46` (46), `36:1-32` (32),
`37:83-113` (31) and `27:15-44` (30).

So a reader at ayah 7 of a 20-ayah block sees commentary written about the whole
passage, with no indication that it is not about ayah 7 specifically. **Whether
the range or the ayah is the display unit is eng-lead's call**, and the numbers
above are what it should be decided on. This data fans out; nothing about that is
irreversible.

## Reproducing this

```bash
# 1. fetch the twelve .docx sources from DIdI (category 3-quelldateien)
#    https://www.didi-info.de/tafsirdateien   -> band1.docx … band12.docx
# 2. regenerate
python3 tools/extract-mourad-tafsir.py <dir-with-band1..band12.docx> tafsir/de-mourad
```

The script is `tools/extract-mourad-tafsir.py`, one file, stdlib only. Its
docstring is the record of every trap in this source shape and why each rule is
the shape it is. It prints the full report above on every run, including the
tripwire counts — a run whose numbers differ from this document is a change worth
explaining.
