#!/usr/bin/env python3
"""
Extract Samir Mourad's `Erläuterung des Koran (Tafsīr)` (DIdI e.V., 12 volumes)
from the publisher's own Word source files into rawi-tafsir's per-ayah JSON.

    usage: extract-mourad-tafsir.py <dir-with-band1..band12.docx> <out-dir>

Output shape matches tafsir/fr-al-mukhtasar byte-for-byte in structure:
    tafsir/de-mourad/{surah}/{ayah}.json
    {"text": "...", "ayah": N, "surah": N}
default json.dumps separators, ensure_ascii=False, no trailing newline — the
byte shape the shipped fr/tr/de editions already use.

WHY WORD AND NOT PDF
--------------------
DIdI publishes the print-ready `.docx` for every volume at
https://www.didi-info.de/tafsirdateien (category `3-quelldateien`). Reading those
instead of the public PDFs removes, structurally rather than heuristically, the
two defect classes that dominated the Rassoul extraction:

  * there are no page breaks, so no commentary paragraph is ever split in two
    (Rassoul: 465 truncated records), and
  * there are no running headers or page numbers in the text stream at all
    (they live in word/headerN.xml, which this script never reads).

HOW THE SOURCE IS SHAPED
------------------------
Mourad keys commentary to ayah RANGES. Every block is opened by a heading whose
text ends with the range in square brackets, and the convention is exact — of
1508 range-bearing headings in the 12 volumes, 1508 carry the range as the LAST
token. Body text is unstyled ("Normal"); the heading level is the structure.

    [Heading1] Sure Al-Mulk (Die Herrschaft)
    [Heading2] Die große Belohnung Allahs ... [67:12-14]      <- opens a block
    [-]        Wahrlich, diejenigen, die ... [67:12]          <- HIS OWN RENDERING
    [-]        Und ob ihr euer Wort verbergt ... [67:13]      <- HIS OWN RENDERING
    [-]        Kennt er denn nicht Den, ... [67:14]           <- HIS OWN RENDERING
    [Heading3] Worterläuterungen und Tafsir
    [-]        Wahrlich, diejenigen, ... [67:12] - Ibn Kathir: D.h. ...   <- COMMENTARY
    [ArabischHadith] <Arabic isnād>
    [-]        „Sieben (Arten von Leuten) wird Allah ...“     <- COMMENTARY

TRAPS HANDLED
-------------
1. THE ONE THING THIS EXTRACTION MAY NOT DO is let Mourad's own German ayah
   renderings into the commentary field. Both apps render a verified German
   translation (Bubenheim & Elyas) directly above the tafsir; a second,
   unverified rendering must not appear underneath it unlabelled. The detector is
   POSITIONAL, and it is built before anything else:

     a rendering is a paragraph in the run immediately following a block-opening
     heading, whose text ENDS with an ayah reference for the block's own surah.

   The run is what makes it safe. It stops at the first paragraph that is not a
   rendering, so commentary can never be swallowed.

2. COMMENTARY QUOTES AYAHS TOO, and that is intrinsic to it — a lemma followed
   by the gloss:
       `Er kennt das Innerste der Herzen. [67:13] - D.h. das, was man ...`
   The reference sits MID-paragraph there, not at the end, so requiring the ref
   at the END is what separates a rendering from a lemma. Cross-surah citations
   (`[17:88]`, `[11:13]`) are rejected by the own-surah test as well.

3. THE BASMALA opens most surahs and sits between the heading and the first
   rendering. It is dropped WITHOUT stopping the run — stopping there would let
   every following rendering leak. This is the single highest-cost bug available
   in this script: it silently leaks scripture for a whole surah.

4. MOURAD RE-PRINTS THE RENDERING BLOCK. Under a later sub-heading he often sets
   the same ayahs again as the passage then under discussion (`[2:34-39]` is
   printed at the top of the block and again under `Wie Adam und seine Frau Eva
   auf die Erde kamen`). That second copy is a second unverified rendering and
   must go too.

   What it must NOT take with it is the LEMMA — the ayah phrase Mourad quotes to
   hang a gloss on, which the Rassoul edition kept because it is intrinsic to the
   commentary. The two are told apart by ARITHMETIC, not by length or wording:

       a re-printed rendering block is a run of consecutive ref-terminated
       paragraphs whose ayah numbers are DISTINCT and ASCENDING;
       a lemma sequence repeats ONE ayah (the ayat al-kursijj commentary quotes
       [2:255] ten times), and a lone lemma is a fragment (`einen Sturmwind
       [17:69]`, `Der Koranvers: [39:68]`).

   So a late group is excluded only when it has two or more members with distinct
   ascending ayahs. Single fragments and same-ayah lemma runs stay. A lone LONG
   ref-terminated paragraph is neither, so it is kept and ⚑FLAGGED for native
   review rather than guessed at in either direction.

   Renderings of ANOTHER surah quoted as evidence inside the commentary (the
   numbered `[38:71-86]` block inside surah 2) also stay, on the Rassoul
   precedent that a quotation inside commentary is part of it. They are counted
   and reported, because they are still unverified renderings and the review may
   want them gone.

5. THE HEADING RANGE SOMETIMES UNDERSTATES WHAT IS PRINTED UNDER IT. The block
   titled `[2:153-154]` prints renderings through [2:157]; the heading is simply
   short. Left alone that both leaks the 2:155-157 renderings into commentary AND
   opens a three-ayah hole in coverage. So the rendering run is allowed to run
   past `hi` as long as the ayah numbers keep ascending, and the block's range is
   then EXTENDED to the last ayah the run actually rendered. That one rule closes
   most of the coverage gaps and removes the leak at the same time.

6. HEADINGS AT DEEPER LEVELS ALSO OPEN BLOCKS (52 Heading3, 1 Heading4), which
   subdivide a parent range into finer keying. Heading5/6 ranges do NOT open a
   block: there are only 4, and one of them
   (`Zusammenhang zwischen den Bestimmungen von [2:234] und [2:240]`) is a
   cross-reference in a title rather than a key, so treating that level as
   structural would mis-key it.

7. OVERLAPPING AND REVISITED RANGES. `[67:12-14]` is followed by `[67:13-15]`;
   ayahs 13 and 14 therefore carry commentary from two blocks. Both are kept and
   concatenated in print order, separated by a blank line, exactly as the
   Rassoul extraction did for its repeated markers.

8. SURAH AL-FATIHA HAS NO RANGE HEADING. Its commentary is one section under
   `[Heading1] Sure Al-Fatiha`, so it is assigned to 1:1-7 explicitly and
   counted separately in the report rather than being quietly missed.

9. SURAH INTRODUCTIONS (11 range-less Heading2, e.g. `Einführung zur Sure
   At-Tauba`) belong to no single ayah. Like the surah preamble in the Rassoul
   edition and the English Ibn Kathir edition in the same dataset, they ride on
   the ayah-1 record.

10. PURE-ARABIC PARAGRAPHS (the isnād chains Mourad prints before his German
   translation of each narration) are EXCLUDED by default: they are untranslated
   source apparatus, they would render RTL inside an LTR block, and the German
   rendering that follows them is self-contained. `--keep-arabic` reverses this.
   The count is reported either way — this is a display decision, not a silent one.
"""

import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128,
    111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73,
    54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60,
    49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52,
    44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19,
    26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3,
    6, 3, 5, 4, 5, 6,
]
assert len(AYAH_COUNTS) == 114 and sum(AYAH_COUNTS) == 6236

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# A range key at the very END of a heading. 1508 of 1508 range-bearing headings
# in the 12 volumes satisfy this, so it is the convention and not a guess.
HEAD_RANGE_RE = re.compile(
    r"\[\s*(\d{1,3})\s*:\s*(\d{1,3})\s*(?:[-–—]\s*(\d{1,3}))?\s*\]\s*[.,;:)\"»“]*\s*$"
)
# The same shape, used on a body paragraph to decide "ends in an ayah reference".
TAIL_RANGE_RE = HEAD_RANGE_RE
ANY_RANGE_RE = re.compile(r"\[\s*(\d{1,3})\s*:\s*(\d{1,3})\s*(?:[-–—]\s*(\d{1,3}))?\s*\]")

# Heading levels that may open a commentary block. See trap 6.
OPENING_LEVELS = {"Heading2", "Heading3", "Heading4"}

# Typographically broken heading ranges, repaired explicitly and exhaustively
# rather than with a tolerant regex — the commentary TEXT is untouched, only the
# ayah keying, and every entry is listed so the review can check the reading.
# There is exactly ONE in the 12 volumes; anything else out of range is reported,
# not guessed.
SOURCE_ERRATA = {
    # Surah 20 has 135 ayahs, so `227` is not an ayah. The next heading is
    # [20:128], and this section is the last before it, so it reads as 115-127.
    # Left unrepaired this is a 13-ayah hole — the largest in the corpus.
    (20, 115, 227): (115, 127),
}

# The basmala, in the several spellings the 12 volumes use for it. Compared on
# letters only (case-folded, diacritics and punctuation stripped) so that
# `Allahs`/`Allāhs` and a trailing `!` or `.` cannot cause a miss — a miss here
# leaks a whole surah's renderings (trap 3).
BASMALA_FORMS = [
    "Im Namen Allahs, des Allerbarmers, des Barmherzigen",
    "Im Namen Allāhs, des Allerbarmers, des Barmherzigen",
]

# Section labels that carry no content. Kept as text would add 1600 repetitions
# of the same two words; dropped, the record starts on the commentary itself.
BOILERPLATE_HEADINGS = {
    "worterlauterungen und tafsir",
    "worterlauterung und tafsir",
    "tafsir",
    "erlauterungen",
    "erlauterung",
}

stats = defaultdict(int)


def fold(s):
    """Letters only, lower-cased, diacritics stripped — for robust comparison."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", s.lower())


BASMALA_FOLDED = {fold(b) for b in BASMALA_FORMS}

ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
LATIN_RE = re.compile(r"[A-Za-zÄÖÜäöüß]")

# Print hyphenation is baked into the Word files as ordinary hyphens, not soft
# hyphens (there are zero U+00AD in the 12 volumes), so `Auf-erstehung`,
# `Segnun-gen` and `isla-mischen` would ship as-is and a German reader would see
# every one of them. They cannot be removed by rule: German compounds
# (`Meister-Schüler-Beziehung`) and the Arabic transliterations that fill this
# book (`al-khauf`, `an-nubuwwa`, `Ahlul-kitab`) are legitimately hyphenated.
#
# So the corpus decides. A hyphen is removed only when the two halves joined form
# a word that occurs SOMEWHERE ELSE in these same 12 volumes without the hyphen.
# That is self-validating and needs no dictionary: 319 occurrences join, and the
# 642 Arabic and compound hyphens are left alone because `alkhauf` and
# `MeisterSchüler` never occur.
PUA_RE = re.compile(r"[\uE000-\uF8FF]")
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüßāīūḥṣṭẓʿʾ']+")
HYPHEN_CAND_RE = re.compile(r"([A-Za-zÄÖÜäöüßāīū]{2,})-([a-zäöüß]{2,})")


def is_basmala(text):
    return fold(text) in BASMALA_FOLDED


def is_arabic_only(text):
    """True when a paragraph is Arabic script with no German prose in it.

    Threshold rather than absolute: the isnād paragraphs occasionally carry a
    stray Latin footnote marker or a `(1)`, which must not make them count as
    German. A paragraph with real German in it always has many Latin letters.
    """
    ar = len(ARABIC_RE.findall(text))
    la = len(LATIN_RE.findall(text))
    return ar >= 8 and la <= max(3, ar // 12)


def paragraphs(path):
    """(style, text) for every paragraph in document order.

    Reads ONLY word/document.xml, so running headers and page numbers — which
    live in word/headerN.xml and word/footerN.xml — cannot enter the text stream.
    Table cells are included: several volumes set comparison passages in tables.
    """
    import zipfile
    from xml.etree import ElementTree as ET

    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    out = []
    for p in body.iter(W + "p"):
        pPr = p.find(W + "pPr")
        style = ""
        if pPr is not None:
            st = pPr.find(W + "pStyle")
            if st is not None:
                style = st.get(W + "val") or ""
        buf = []
        for node in p.iter():
            if node.tag == W + "t":
                buf.append(node.text or "")
            elif node.tag == W + "tab":
                buf.append(" ")
            elif node.tag == W + "br":
                buf.append(" ")
        text = "".join(buf)
        # Symbol-font glyphs (Wingdings and the like) arrive as Private Use Area
        # code points. They carry no text and render as tofu on both platforms,
        # so they go before anything else looks at the paragraph — otherwise a
        # paragraph of pure decoration survives as non-empty and ships.
        text = PUA_RE.sub("", text)
        text = re.sub(r"[ \t\u00a0\u200b-\u200d\ufeff]+", " ", text).strip()
        out.append((style, text))
    return out


def tail_ref(text, surah):
    """(a1, a2) when `text` ENDS with an ayah reference for `surah`, else None.

    Ending is what separates a rendering from a lemma: Mourad's renderings close
    with the reference, while his glosses carry it mid-paragraph
    (`… [67:13] - D.h. …`). A paragraph carrying MORE THAN ONE distinct reference
    is a citation list (`Ausführliche Koranverse …: [22:26-27], [3:96-97],
    [2:124-129].`) and is never a rendering.
    """
    m = TAIL_RANGE_RE.search(text)
    if not m or int(m.group(1)) != surah:
        return None
    refs = {(int(a), int(b), c) for a, b, c in ANY_RANGE_RE.findall(text)}
    if len({(a, b) for a, b, _ in refs}) > 1:
        return None
    a1 = int(m.group(2))
    a2 = int(m.group(3)) if m.group(3) else a1
    if not (1 <= a1 <= AYAH_COUNTS[surah - 1] and a1 <= a2 <= AYAH_COUNTS[surah - 1]):
        return None
    return a1, a2


# A paragraph that is ref-terminated but ALSO attributes a gloss is a lemma or a
# citation, not a rendering. Case-insensitive: `Siehe auch: [2:122-123].` and
# `siehe auch` both occur, and missing the capitalised form drops a
# cross-reference line that belongs to the commentary.
COMMENTARY_MARKERS = re.compile(
    r"(Ibn Kathir|Ibn Kathīr|Az-Zuhaili|Az-Zuḥailī|Tabari|Aṭ-Ṭabarī|Qurtubi|"
    r"Sayyid Qutb|Albani|D\.\s*h\.|sagt|sagte|berichtet|berichtete|bedeutet|"
    r"Anmerkung|siehe|vgl\.|Koranvers:|\[\s*…\s*\]|\[\.\.\.\])",
    re.IGNORECASE,
)

# Below this length a ref-terminated paragraph is a fragment, so it is a lemma
# and not a rendering of a whole ayah. Chosen from the observed set: the shortest
# genuine standalone renderings run ~90 chars, while the lemma fragments
# (`einen Sturmwind [17:69]`, `große, harte Steine [11:82]`) are all under 35.
LEMMA_MAX_CHARS = 60

# A lone ref-terminated paragraph at least this long, sitting after commentary
# has begun and outside any ascending group, is neither clearly a lemma nor
# clearly a re-print. It is KEPT and flagged for native review.
FLAG_MIN_CHARS = 150


def ascending_group(ps, start, surah, seen_upto):
    """Length of the run of consecutive ref-terminated paragraphs from `start`
    whose ayah numbers are DISTINCT and STRICTLY ASCENDING.

    This is the arithmetic that separates a re-printed rendering block (2:34,
    2:35, 2:36 …) from a lemma sequence that repeats one ayah ([2:255] ten
    times). Blank paragraphs are skipped; anything else ends the run.
    """
    out = []
    last = None
    i = start
    while i < len(ps):
        style, text = ps[i]
        if not text:
            i += 1
            continue
        if style.startswith("Heading"):
            break
        r = tail_ref(text, surah)
        if r is None or len(text) < LEMMA_MAX_CHARS:
            break
        if last is not None and r[0] <= last:
            break
        last = r[1]
        out.append(i)
        i += 1
    return out


def build_vocab(volumes):
    """Every word that occurs anywhere in the corpus, lower-cased."""
    vocab = set()
    for ps in volumes:
        for _style, text in ps:
            if text:
                for w in WORD_RE.findall(text):
                    vocab.add(w.lower())
    return vocab


def dehyphenate(text, vocab):
    """Undo print hyphenation, but only where the corpus proves the join."""
    def repl(m):
        a, b = m.group(1), m.group(2)
        if (a + b).lower() in vocab:
            stats["hyphens_joined"] += 1
            return a + b
        return m.group(0)
    return HYPHEN_CAND_RE.sub(repl, text)


def main():
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    keep_arabic = "--keep-arabic" in sys.argv

    # (surah, ayah) -> list of block texts, in print order
    records = defaultdict(list)
    # (surah, a1, a2) -> emitted, for the range distribution report
    blocks = []
    excluded_renderings = []
    late_hits = []
    flagged = []
    rejected_headings = []
    unkeyed_sections = []
    heading_texts = set()
    preambles = defaultdict(list)
    arabic_dropped = 0

    volumes = []
    for vol in range(1, 13):
        path = os.path.join(src_dir, f"band{vol}.docx")
        if not os.path.exists(path):
            raise SystemExit(f"missing source: {path}")
        volumes.append(paragraphs(path))
    vocab = build_vocab(volumes)

    for vol in range(1, 13):
        ps = [(st, dehyphenate(t, vocab) if t else t) for st, t in volumes[vol - 1]]
        stats["paragraphs"] += len(ps)

        cur = None          # (surah, lo, hi, [lines])
        surah_ctx = None    # from the last Heading1, for the Fatiha / preamble cases
        seen_range_in_surah = False
        pending_preamble = []

        def flush():
            nonlocal cur
            if cur is None:
                return
            surah, lo, hi, lines = cur
            text = "\n\n".join(x for x in lines if x)
            if text.strip():
                blocks.append((surah, lo, hi))
                for a in range(lo, hi + 1):
                    if 1 <= a <= AYAH_COUNTS[surah - 1]:
                        records[(surah, a)].append(text)
            cur = None

        def close_rangeless_surah():
            """Trap 8: a surah whose section carries no range heading at all.

            Only al-Fatiha does this. Its whole section is one block over every
            ayah of the surah. Without this the seven records are silently empty,
            which is exactly the 'partial extraction claiming completeness'
            failure — so it is counted, not assumed.
            """
            nonlocal pending_preamble
            if seen_range_in_surah or surah_ctx is None or not pending_preamble:
                return
            body = "\n\n".join(x for x in pending_preamble if x)
            if body.strip():
                n = AYAH_COUNTS[surah_ctx - 1]
                blocks.append((surah_ctx, 1, n))
                for a in range(1, n + 1):
                    records[(surah_ctx, a)].append(body)
                stats["rangeless_surah_blocks"] += 1
            pending_preamble = []

        i = 0
        while i < len(ps):
            style, text = ps[i]

            if not text:
                i += 1
                continue

            # ---- Heading1: a new surah -------------------------------------
            if style == "Heading1":
                flush()
                close_rangeless_surah()
                surah_ctx = None
                seen_range_in_surah = False
                pending_preamble = []
                # The volume order is the surah order, so resolve the surah from
                # the next range heading rather than by parsing the German name.
                for k in range(i + 1, min(i + 400, len(ps))):
                    s2, t2 = ps[k]
                    if s2.startswith("Heading") and t2:
                        m2 = HEAD_RANGE_RE.search(t2)
                        if m2:
                            surah_ctx = int(m2.group(1))
                            break
                    if s2 == "Heading1" and k > i:
                        break
                if surah_ctx is None:
                    # No range heading anywhere in this section. Resolve it from
                    # the NEXT section's surah number minus one: the volumes run
                    # in surah order, so the section before surah N is N-1. Only
                    # al-Fatiha needs this, and deriving it beats hard-coding 1.
                    for k in range(i + 1, len(ps)):
                        s2, t2 = ps[k]
                        if s2.startswith("Heading") and t2:
                            m2 = HEAD_RANGE_RE.search(t2)
                            if m2:
                                nxt = int(m2.group(1))
                                if 2 <= nxt <= 114:
                                    surah_ctx = nxt - 1
                                break
                    stats["surah_without_any_range_heading"] += 1
                i += 1
                continue

            # ---- a block-opening heading -----------------------------------
            m = HEAD_RANGE_RE.search(text) if style in OPENING_LEVELS else None
            if m:
                flush()
                surah = int(m.group(1))
                lo = int(m.group(2))
                hi = int(m.group(3)) if m.group(3) else lo
                if (surah, lo, hi) in SOURCE_ERRATA:
                    lo, hi = SOURCE_ERRATA[(surah, lo, hi)]
                    stats["errata_applied"] += 1
                if not (1 <= surah <= 114) or hi < lo or hi > AYAH_COUNTS[surah - 1]:
                    rejected_headings.append((surah, lo, hi, text))
                    stats["heading_range_rejected"] += 1
                    i += 1
                    continue
                surah_ctx = surah
                title = ANY_RANGE_RE.sub("", text).strip(" .,;:-–—")
                lines = [title] if title else []
                if title:
                    heading_texts.add(title)
                # A surah introduction seen before the first range heading rides
                # on ayah 1 (trap 9).
                if not seen_range_in_surah and pending_preamble:
                    preambles[surah].extend(pending_preamble)
                    pending_preamble = []
                seen_range_in_surah = True

                # ---- THE RENDERING RUN (traps 1, 3, 5) ---------------------
                j = i + 1
                last_ayah = None
                while j < len(ps):
                    s2, t2 = ps[j]
                    if s2.startswith("Heading"):
                        break
                    if not t2:
                        j += 1
                        continue
                    if is_basmala(t2):
                        stats["basmala_dropped"] += 1
                        j += 1
                        continue          # trap 3: drop WITHOUT stopping
                    r = tail_ref(t2, surah)
                    # Trap 5: keep going past `hi` while the ayahs ascend, and
                    # widen the block to what was actually rendered. The first
                    # rendering must start at or near `lo`, which is what stops
                    # a stray ref-terminated line from opening a bogus run.
                    if r is not None and (
                        (last_ayah is None and lo - 2 <= r[0] <= hi + 2)
                        or (last_ayah is not None and r[0] > last_ayah)
                    ):
                        excluded_renderings.append((surah, lo, hi, t2))
                        stats["renderings_excluded"] += 1
                        stats["rendering_chars"] += len(t2)
                        last_ayah = r[1]
                        if r[1] > hi:
                            hi = min(r[1], AYAH_COUNTS[surah - 1])
                            stats["block_range_extended"] += 1
                        j += 1
                        continue
                    break                 # commentary starts here
                cur = (surah, lo, hi, lines)
                i = j
                continue

            # ---- any other heading: a sub-section label --------------------
            if style.startswith("Heading") or style in ("Zwischenberschrift",
                                                        "berschriftohneNummer"):
                if fold(text) in BOILERPLATE_HEADINGS:
                    stats["boilerplate_heading_dropped"] += 1
                    i += 1
                    continue
                # A range-LESS Heading2 in the middle of a surah is a section
                # whose key the book never printed (11 of them across the 12
                # volumes). Its content stays attached to the block above rather
                # than being keyed by inference: the interval it would occupy is
                # reported instead, so the gap is visible and the decision to
                # close it stays with the review. Guessing here would silently
                # move commentary onto ayahs the author never keyed it to.
                if style == "Heading2" and cur is not None and seen_range_in_surah:
                    nxt = None
                    for k in range(i + 1, len(ps)):
                        s3, t3 = ps[k]
                        if s3.startswith("Heading") and t3:
                            m3 = HEAD_RANGE_RE.search(t3)
                            if m3 and int(m3.group(1)) == cur[0]:
                                nxt = int(m3.group(2))
                                break
                    unkeyed_sections.append((cur[0], cur[2] + 1,
                                             (nxt - 1) if nxt else None, text))
                    stats["unkeyed_sections"] += 1
                heading_texts.add(text)
                if cur is not None:
                    cur[3].append(text)
                elif not seen_range_in_surah:
                    pending_preamble.append(text)
                i += 1
                continue

            # ---- body paragraph -------------------------------------------
            if is_basmala(text):
                stats["basmala_dropped"] += 1
                i += 1
                continue

            if is_arabic_only(text):
                arabic_dropped += 1
                if not keep_arabic:
                    i += 1
                    continue

            if cur is not None:
                surah, lo, hi, lines = cur
                # ---- trap 4: a RE-PRINTED rendering block -------------------
                # Only an ascending group of two or more is a re-print. A single
                # fragment or a same-ayah lemma run is intrinsic and stays.
                grp = ascending_group(ps, i, surah, hi)
                if len(grp) >= 2:
                    for k in grp:
                        late_hits.append((surah, lo, hi, ps[k][1]))
                        stats["late_renderings_excluded"] += 1
                    i = grp[-1] + 1
                    continue
                # A lone long ref-terminated paragraph: keep it, and flag it.
                r = tail_ref(text, surah)
                if (r is not None and len(text) >= FLAG_MIN_CHARS
                        and not COMMENTARY_MARKERS.search(text)):
                    flagged.append((surah, lo, hi, text))
                    stats["flagged_for_review"] += 1
                lines.append(text)
            elif not seen_range_in_surah:
                # A range-less section accumulates here — including al-Fatiha,
                # whose entire commentary arrives this way. Mourad prints his
                # renderings at the top of it exactly as he does under a range
                # heading, so the SAME exclusion has to apply: without this the
                # seven Fatiha records each carry his rendering of 1:2-1:7, which
                # is the cardinal rule broken on the most-read surah in the app.
                if surah_ctx is not None and tail_ref(text, surah_ctx) is not None:
                    excluded_renderings.append((surah_ctx, 1,
                                                AYAH_COUNTS[surah_ctx - 1], text))
                    stats["renderings_excluded"] += 1
                    stats["rendering_chars"] += len(text)
                    stats["renderings_excluded_in_rangeless"] += 1
                else:
                    pending_preamble.append(text)
            else:
                stats["orphan_paragraph"] += 1
            i += 1

        flush()
        close_rangeless_surah()

        if pending_preamble:
            stats["unplaced_preamble_paragraphs"] += len(pending_preamble)

    # ---- preambles ride on ayah 1 ------------------------------------------
    for surah, parts in preambles.items():
        body = "\n\n".join(parts)
        if body.strip():
            records[(surah, 1)].insert(0, body)
            stats["preambles_attached"] += 1

    # ---- final pass: no text the detector already called a rendering may -----
    # ---- survive anywhere in the corpus --------------------------------------
    # Mourad re-quotes a full ayah as the anchor for its gloss, often alternating
    # rendering / gloss so the re-print is never two in a row and the ascending-
    # group test (trap 4) cannot see it. Rather than guess from length, match on
    # CONTENT: every paragraph the rendering run already excluded is known, so any
    # paragraph that reproduces one is the same rendering a second time and goes.
    # This is exact, and it is what makes the cardinal rule a guarantee rather
    # than a heuristic — a full rendering cannot reach a commentary field unless
    # it never appeared in a rendering run at all.
    def norm(t):
        t = unicodedata.normalize("NFKD", t)
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]", "", t.lower())

    # BOTH exclusion sets feed the index. Building it from the rendering runs
    # alone leaves a hole: a rendering that also appears as a re-printed block can
    # turn up a THIRD time and survive, because nothing in the index matches it.
    # 41 paragraphs came back that way before late_hits was included here.
    rendering_keys = set()
    for surah, _lo, _hi, t in list(excluded_renderings) + list(late_hits):
        n = norm(t)
        if len(n) >= 40:
            rendering_keys.add((surah, n))

    for (s_, a_), parts in list(records.items()):
        kept = []
        for t in parts:
            out_paras = []
            for para in t.split("\n\n"):
                n = norm(para)
                if len(n) >= 40 and (s_, n) in rendering_keys:
                    stats["duplicate_rendering_removed"] += 1
                    continue
                out_paras.append(para)
            joined = "\n\n".join(x for x in out_paras if x.strip())
            if joined.strip():
                kept.append(joined)
        records[(s_, a_)] = kept

    for k in [k for k, v in records.items() if not v]:
        del records[k]
        stats["records_emptied_by_dedupe"] += 1

    # ---- write --------------------------------------------------------------
    written = 0
    for (s, a), parts in sorted(records.items()):
        text = "\n\n".join(parts)
        d = os.path.join(out_dir, str(s))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{a}.json"), "w", encoding="utf-8") as f:
            # Default separators, no trailing newline — byte-identical in shape
            # to the shipped fr/tr/de editions (`{"text": "…", "ayah": N, …}`).
            json.dump({"text": text, "ayah": a, "surah": s}, f,
                      ensure_ascii=False)
        written += 1

    # ---- report -------------------------------------------------------------
    gaps = {}
    for s in range(1, 115):
        miss = [a for a in range(1, AYAH_COUNTS[s - 1] + 1) if (s, a) not in records]
        if miss:
            gaps[s] = miss
    total_gaps = sum(len(v) for v in gaps.values())

    print(f"paragraphs read: {stats['paragraphs']}")
    print(f"commentary blocks: {len(blocks)}")
    print(f"records written: {written} / 6236 ({written / 6236 * 100:.2f}%)")
    print(f"missing ayahs: {total_gaps}")
    print()
    print(f"renderings excluded (run after heading): {stats['renderings_excluded']} "
          f"({stats['rendering_chars']:,} chars)")
    print(f"renderings excluded (re-printed blocks, after commentary began): "
          f"{stats['late_renderings_excluded']}")
    print(f"⚑ lone ref-terminated paragraphs KEPT and flagged for native review: "
          f"{stats['flagged_for_review']}")
    print(f"block ranges widened past the heading: {stats['block_range_extended']}")
    print(f"basmala paragraphs dropped: {stats['basmala_dropped']}")
    print(f"pure-Arabic paragraphs {'kept' if keep_arabic else 'dropped'}: {arabic_dropped}")
    print(f"boilerplate headings dropped: {stats['boilerplate_heading_dropped']}")
    print(f"surah preambles attached to ayah 1: {stats['preambles_attached']}")
    print(f"range-less surahs blocked whole (al-Fatiha): "
          f"{stats['rangeless_surah_blocks']}")
    print(f"  of those, inside a range-less section (al-Fatiha): "
          f"{stats['renderings_excluded_in_rangeless']}")
    print(f"print hyphens rejoined (corpus-validated): {stats['hyphens_joined']}")
    print(f"duplicate renderings removed from commentary (content match): "
          f"{stats['duplicate_rendering_removed']}")
    print(f"records emptied by that dedupe: {stats['records_emptied_by_dedupe']}")
    print(f"orphan paragraphs (no open block): {stats['orphan_paragraph']}")
    print(f"unplaced preamble paragraphs: {stats['unplaced_preamble_paragraphs']}")
    print(f"source errata applied to heading ranges: {stats['errata_applied']}")
    print(f"headings STILL rejected as out-of-range: {stats['heading_range_rejected']}")
    for su, lo, hi, t in rejected_headings:
        print(f"      ⚑ [{su}:{lo}-{hi}] {t[:90]}")
    print(f"⚑ range-less sections left attached to the block above: "
          f"{stats['unkeyed_sections']}")
    for su, lo, hi, t in unkeyed_sections:
        span = f"{su}:{lo}-{hi}" if hi and hi >= lo else f"{su}:{lo}-?"
        print(f"      would occupy {span}  — {t[:76]}")

    sizes = defaultdict(int)
    for _, a1, a2 in blocks:
        sizes[a2 - a1 + 1] += 1
    print("\nrange size -> count:")
    for k in sorted(sizes):
        print(f"   {k:3d} ayahs : {sizes[k]}")
    multi = sum(v for k, v in sizes.items() if k > 1)
    print(f"single-ayah blocks: {sizes.get(1, 0)}   multi-ayah blocks: {multi}")
    biggest = sorted(blocks, key=lambda b: b[2] - b[1], reverse=True)[:10]
    print("largest blocks:", [f"{s}:{a}-{b} ({b-a+1})" for s, a, b in biggest])
    print(f"ayahs whose text comes from >1 block: "
          f"{sum(1 for v in records.values() if len(v) > 1)}")

    if gaps:
        print(f"\ngaps — {len(gaps)} surahs:")
        for s in sorted(gaps):
            print(f"   surah {s}: {len(gaps[s])}/{AYAH_COUNTS[s-1]} missing {gaps[s][:16]}"
                  f"{'…' if len(gaps[s]) > 16 else ''}")

    # ---- tripwires ----------------------------------------------------------
    # The point of this section is to answer, from the WRITTEN corpus rather than
    # from the parser's own bookkeeping, the one question that matters: did an
    # unverified rendering of this ayah reach this ayah's commentary field?
    print("\ntripwires —")
    own_ayah_long = []     # in-block, full-ayah length: the review queue
    own_ayah_frag = 0      # in-block, fragmentary: an intrinsic lemma
    other_ayah_quote = 0   # a quotation of some other ayah: intrinsic, per Rassoul
    for (s, a), parts in records.items():
        for t in parts:
            for para in t.split("\n\n"):
                if para in heading_texts:
                    continue          # a section title, not a rendering
                r = tail_ref(para, s)
                if r is None or len(para) < LEMMA_MAX_CHARS:
                    continue
                if COMMENTARY_MARKERS.search(para):
                    continue
                if r[0] <= a <= r[1]:
                    if len(para) >= FLAG_MIN_CHARS:
                        own_ayah_long.append((s, a, para))
                    else:
                        own_ayah_frag += 1
                else:
                    other_ayah_quote += 1
    print(f"   ⚠ ref-terminated paragraphs of THIS ayah, full-ayah length — the"
          f" ⚑review queue: {len(own_ayah_long)}")
    for s, a, para in own_ayah_long[:8]:
        print(f"      {s}:{a}  {para[:120]!r}")
    print(f"   fragmentary lemmas of this ayah, kept as intrinsic: {own_ayah_frag}")
    print(f"   quotations of a DIFFERENT ayah, kept as intrinsic: {other_ayah_quote}")
    arabic_left = sum(1 for v in records.values() for t in v
                      for para in t.split("\n\n") if is_arabic_only(para))
    print(f"   pure-Arabic paragraphs surviving in output: {arabic_left}")
    empt = [f"{s}:{a}" for (s, a), v in records.items() if not "\n\n".join(v).strip()]
    print(f"   empty records: {len(empt)} {empt[:6]}")

    lens = sorted(len("\n\n".join(v)) for v in records.values())
    print(f"\ntext length chars: min={lens[0]} p05={lens[int(len(lens)*.05)]} "
          f"p50={lens[len(lens)//2]} p95={lens[int(len(lens)*.95)]} max={lens[-1]}")

    with open(os.path.join(out_dir, "_coverage.json"), "w") as f:
        json.dump({
            "written": written,
            "blocks": len(blocks),
            "gaps": {str(k): v for k, v in gaps.items()},
            "renderings_excluded": stats["renderings_excluded"],
            "late_renderings_excluded": stats["late_renderings_excluded"],
            "arabic_paragraphs_dropped": arabic_dropped,
            "range_sizes": {str(k): v for k, v in sorted(sizes.items())},
            "review_queue": len(own_ayah_long),
            "duplicate_renderings_removed": stats["duplicate_rendering_removed"],
            "flagged_for_review": stats["flagged_for_review"],
        }, f, indent=1, ensure_ascii=False)

    # a full dump of what the detector removed, so the review can audit it
    with open(os.path.join(out_dir, "_excluded_renderings.txt"), "w",
              encoding="utf-8") as f:
        for s, lo, hi, t in excluded_renderings:
            f.write(f"[{s}:{lo}-{hi}]\t{t}\n")
        f.write("\n==== RE-PRINTED BLOCKS (after commentary began) ====\n")
        for s, lo, hi, t in late_hits:
            f.write(f"[{s}:{lo}-{hi}]\t{t}\n")
        f.write("\n==== KEPT BUT FLAGGED FOR NATIVE REVIEW (\u2691) ====\n")
        for s, lo, hi, t in flagged:
            f.write(f"[{s}:{lo}-{hi}]\t{t}\n")


if __name__ == "__main__":
    main()
