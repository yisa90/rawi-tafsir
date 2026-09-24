#!/usr/bin/env python3
"""Generate the golden fixture: one `.rtb` that three readers must agree on.

    python3 tools/tests/make_fixture.py

Writes, all committed:

    tools/tests/fixtures/fixture-edition.rtb
    tools/tests/fixtures/fixture-manifest.json
    tools/tests/fixtures/fixture-expectations.json

**This fixture is a parity contract, not a Python test asset.** The iOS and
Android readers vendor the same three files and assert the same expectations,
so "the Android reader mirrors the iOS one" is checked mechanically instead of
by reading two diffs. A reader that passes `fixture-expectations.json` and a
reader that does not are distinguishable without a human.

It deliberately contains the cases the nine shipping editions do NOT all have:

  * 125 ayahs with no commentary (no shipping edition has any right now — the
    German edition that had them was dropped. Without this, the missing-record
    contract would be tested only against zero);
  * range blocks, including the 2:1-20 shape the German Mourad edition keys to;
  * a block shared by 2:286 and 3:1 — adjacent ordinals, different surahs. A
    reader that derives coverage without clamping to the surah reports
    "covers 2:286-3:1", which is the bug this case exists to catch;
  * a block shared by two far-apart ayahs, which must read as a single ayah on
    both sides, not as a 6000-ayah range;
  * a block larger than the 128 KiB chunk target, which must get its own chunk;
  * multi-byte UTF-8 at block boundaries.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from rtb_format import (  # noqa: E402
    AYAH_COUNT,
    DEFAULT_CHUNK_BYTES,
    ayah_order_digest,
    iter_positions,
    ordinal,
    position,
)
import rtb_writer as api  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")

# Contiguous runs sharing one block. 2:1-20 is the Mourad shape.
RANGES = [(2, 1, 20), (2, 21, 29), (7, 11, 25), (1, 1, 7), (114, 1, 6)]
# Same text, adjacent ordinals, different surahs — coverage must clamp.
BOUNDARY_TWINS = [(2, 286), (3, 1)]
# Same text, far apart — each must read as one ayah.
DISTANT_TWINS = [(5, 10), (90, 2)]
OVERSIZE = (12, 3)
HOLE_COUNT = 125

FLAVOUR = "بِسْمِ ٱللَّٰهِ — Erläuterung — précis — açıklama"


def build_texts():
    reserved = set()
    for s, a0, a1 in RANGES:
        for a in range(a0, a1 + 1):
            reserved.add(ordinal(s, a))
    for s, a in BOUNDARY_TWINS + DISTANT_TWINS + [OVERSIZE]:
        reserved.add(ordinal(s, a))

    holes = []
    for n in range(AYAH_COUNT):
        if len(holes) == HOLE_COUNT:
            break
        if n % 50 in (7, 23) and n not in reserved:
            holes.append(n)
    holes = set(holes)

    texts = [None] * AYAH_COUNT
    for n, (s, a) in enumerate(iter_positions()):
        if n in holes:
            continue
        texts[n] = "Fixture commentary for %d:%d. %s" % (s, a, FLAVOUR)

    for i, (s, a0, a1) in enumerate(RANGES):
        shared = ("Fixture range block %d covering %d:%d-%d. %s"
                  % (i, s, a0, a1, FLAVOUR))
        for a in range(a0, a1 + 1):
            texts[ordinal(s, a)] = shared

    for s, a in BOUNDARY_TWINS:
        texts[ordinal(s, a)] = "Fixture boundary twin. %s" % FLAVOUR
    for s, a in DISTANT_TWINS:
        texts[ordinal(s, a)] = "Fixture distant twin. %s" % FLAVOUR

    # > 128 KiB, and compressible but not trivially so.
    big = []
    for i in range(3000):
        big.append("Oversize paragraph %d of the fixture block; %s"
                   % (i, FLAVOUR[i % len(FLAVOUR):] + FLAVOUR[:i % len(FLAVOUR)]))
    texts[ordinal(*OVERSIZE)] = "\n".join(big)

    return texts, sorted(holes)


EDITION = {
    "id": 999999,
    "slug": "fixture-edition",
    "name": "Fixture Edition",
    "author": "rawi-tafsir tools",
    "language": "xx",
    "attribution": "Fixture attribution — a reader must not hand back text without this.",
    "attribution_required": True,
    "awaiting_scholarly_review": True,
}


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    texts, holes = build_texts()
    blocks, ayah_index = api.build_blocks(texts)
    data, stats = api.serialize(blocks, ayah_index, DEFAULT_CHUNK_BYTES)

    rtb_path = os.path.join(FIXTURES, "fixture-edition.rtb")
    with open(rtb_path, "wb") as fh:
        fh.write(data)

    import hashlib
    row = dict(EDITION)
    row.update({
        "file": "fixture-edition.rtb",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "blocks": stats["blocks"],
        "chunks": stats["chunks"],
        "ayahs_with_commentary": AYAH_COUNT - len(holes),
        "ayahs_without_commentary": len(holes),
    })

    sys.path.insert(0, os.path.dirname(HERE))
    import rtb_reader
    bundle = rtb_reader.open_bundle(rtb_path, row)
    row["max_coverage_run"] = bundle.max_coverage_run()

    manifest = {
        "schema": 1,
        "bundle_version": "fixture",
        "source_commit": None,
        "ayah_count": AYAH_COUNT,
        "ayah_order_version": ayah_order_digest(),
        "chunk_target_bytes": DEFAULT_CHUNK_BYTES,
        "compression": "deflate-raw-9",
        "generator": "tools/tests/make_fixture.py",
        "editions": [row],
    }
    with open(os.path.join(FIXTURES, "fixture-manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # Everything a platform reader must reproduce, value for value.
    def probe(s, a):
        r = bundle.read(s, a)
        if r is rtb_reader.NO_COMMENTARY_RESULT:
            return {"surah": s, "ayah": a, "state": "noCommentary"}
        return {
            "surah": s, "ayah": a, "state": "text",
            "text_sha256": __import__("hashlib").sha256(
                r.text.encode("utf-8")).hexdigest(),
            "text_utf8_bytes": len(r.text.encode("utf-8")),
            "attribution": r.attribution,
            "coverage_start_ayah": r.coverage.start_ayah,
            "coverage_end_ayah": r.coverage.end_ayah,
            "is_range": r.coverage.is_range,
        }

    probes = []
    for s, a0, a1 in RANGES:
        for a in (a0, (a0 + a1) // 2, a1):
            probes.append(probe(s, a))
    for s, a in BOUNDARY_TWINS + DISTANT_TWINS + [OVERSIZE]:
        probes.append(probe(s, a))
    for n in holes[:3] + holes[-1:]:
        probes.append(probe(*position(n)))
    for s, a in [(1, 1), (2, 30), (36, 1), (55, 13), (114, 6)]:
        probes.append(probe(s, a))

    expectations = {
        "_comment": (
            "Golden expectations for the .rtb v1 reader. iOS, Android and the "
            "Python reference reader all assert these. If a platform reader "
            "disagrees with a value here, that reader is wrong."),
        "file": "fixture-edition.rtb",
        "sha256": row["sha256"],
        "bytes": row["bytes"],
        "format_version": 1,
        "ayah_count": AYAH_COUNT,
        "block_count": row["blocks"],
        "chunk_count": row["chunks"],
        "chunk_target_bytes": DEFAULT_CHUNK_BYTES,
        "ayah_order_version": ayah_order_digest(),
        "ayahs_without_commentary": row["ayahs_without_commentary"],
        "max_coverage_run": row["max_coverage_run"],
        "no_commentary_ordinals": holes,
        "oversize_block_is_alone_in_its_chunk": True,
        "refusal_cases": [
            {
                "name": "attribution_required with no attribution",
                "manifest_row_override": {"attribution": None},
                "expect": "bundleUnreadable",
            },
            {
                "name": "sha256 mismatch",
                "manifest_row_override": {"sha256": "0" * 64},
                "expect": "bundleUnreadable",
            },
        ],
        "probes": probes,
    }
    with open(os.path.join(FIXTURES, "fixture-expectations.json"), "w") as fh:
        json.dump(expectations, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("fixture-edition.rtb  %d bytes  %d blocks  %d chunks  %d without "
          "commentary  max run %d"
          % (row["bytes"], row["blocks"], row["chunks"],
             row["ayahs_without_commentary"], row["max_coverage_run"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
