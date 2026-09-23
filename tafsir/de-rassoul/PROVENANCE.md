# de-rassoul — provenance, licence, and honest coverage

## Edition

**Tafsīr Al-Qurʾān Al-Karīm** (monolingual German)
Abū-r-Riḍāʾ Muḥammad Ibn Aḥmad Ibn Rassoul
IB Verlag Islamische Bibliothek, Düsseldorf
41st revised and expanded edition, Ṣafar 1429 / March 2008
(retitled from *Die ungefähre Bedeutung des Al-Qurʾān Al-Karīm*)

Digitised script prepared by Bešir Kadrioski (25 Rajab 1430 / 18 July 2009)
from a working file supplied by the author, and published as a free PDF.

Source file: `https://www.islamicbulletin.org/german/ebooks/koran/tafsir_al_quran.pdf`
(1093 pages, 5.8 MB).

## Licence — attribution is a condition, not a courtesy

Printed in the book under *Nachdruck*:

> Die Vervielfältigung, der Nachdruck und die Übersetzung dieses Werkes in eine
> Fremdsprache sind erlaubt, wenn dabei auf diese Quelle hingewiesen wird.

Reproduction, reprinting and translation are permitted **provided the source is
credited**. The permission is conditional on the credit. A surface that renders
this edition without naming it is outside the licence, so the attribution is
carried in each app's tafsir catalogue rather than being left to the UI:

- iOS: `Ayah/Tafsir/TafsirCatalog.swift` → `TafsirEntry.attribution`
- Android: `core/model/.../TafsirInfo.kt` → `TafsirInfo.attribution`

Both platforms have a test that fails if this edition's attribution is empty.

The transliteration uses `Ḫ`/`ḫ` for خ, per the digitiser's note, and `’`
(U+2019) rather than `ʾ` for hamza. Both are the source's own conventions and
are reproduced unchanged.

## Coverage — 6111 of 6236 ayahs (98.00%)

Per-ayah records exist for 6111 of the 6236 ayahs. **The 125 missing ayahs are
gaps in the printed book, not extraction failures**: Rassoul keys his commentary
to individual ayahs and ayah ranges and does not comment on every ayah. Each of
the 125 was checked against every column-0 reference line in the source; none is
covered by a marker anywhere in the book.

Missing, as contiguous runs:

```
4:71      5:42-43    6:46-49, 63-64     9:104     11:115
12:15, 51-53, 57, 90-92    13:4    14:43    20:91   21:25
23:102-104   25:44   26:37, 186-191     27:46-47, 72-75, 92-93
28:19   29:32-35   34:33   37:150-160    39:15-16, 66
40:22, 48-50, 81   41:8, 18, 22   43:55-56   52:30-34   53:16-17
55:55-61   56:57-58   62:8   67:12-15   70:3-4   71:2-4
72:20-24   74:26-29   79:16-26   86:5, 15   90:6-10
```

**Both apps currently surface a missing record as a network error.** That is
wrong for this edition and is an open product decision, not a data problem.

## What is in a record, and what is deliberately not

- **Commentary only.** Rassoul's own German renderings of the ayahs (1887
  paragraphs, ~940 KB) are **excluded**. Both apps already render a verified
  German ayah translation (Bubenheim & Elyas) above the tafsir; a second,
  unverified rendering must not enter the commentary field. Ayah phrases quoted
  *inside* the commentary are intrinsic to it and are kept.
- **Surah preambles** belong to no single ayah and are prepended to the ayah-1
  record, together with the printed header (`(1) Sura Al-Fātiḥa (Die
  Eröffnende)` / `(offenbart zu Makka)` / `7 Āyāt`). This is the convention the
  English Ibn Kathir edition in this same repo already uses.
- **Range commentary** (`11:51-60 - …`) is replicated onto every ayah in the
  range, as `scripts/convert-qul-tafsir.sh` already does for the fr/tr editions.
  4561 ayahs get their text this way.
- **Repeat notes.** Rassoul revisits some ayahs (`2:31` twice) and uses
  overlapping ranges (`11:50-52` then `11:51-60`). Both notes are kept, in print
  order, separated by a blank line.
- **Running headers** (976) and **page numbers** (975) are stripped.

## Source errata applied

Two marker lines in the 41st edition are typographically broken. Only the ayah
keying was repaired; the commentary text is untouched.

| Printed | Read as | Why |
|---|---|---|
| `3:119-1120 - …` | 3:119–120 | 1120 is not an ayah; surah 3 ends at 200, and 3:120 is otherwise uncommented |
| `55:8-10-12 - …` | 55:8–12 | doubled range dash; 55:11 and 55:12 are otherwise uncommented |

## Scholarly review

**Not yet reviewed.** This edition is scripture-adjacent commentary from a 2008
devotional work. pm-deen prepares the review; a human scholar rules. The
ADR-013 scholar-of-record slot is still empty.
