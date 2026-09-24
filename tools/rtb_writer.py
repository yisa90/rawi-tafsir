"""Writer side of the `.rtb` v1 container: source tree -> blocks -> chunks.

Imported by `build-bundles.py` (the CLI) and by `tests/make_fixture.py`. Kept
importable on purpose — the CLI's filename has a hyphen in it and cannot be.
"""

import hashlib
import json
import os

from rtb_format import (
    AYAH_COUNT,
    FLAG_DEFLATE_RAW,
    HEADER_SIZE,
    MAX_BLOCK_ID,
    NO_COMMENTARY,
    iter_positions,
    pack_header,
)
import zlib


class BuildError(Exception):
    pass


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_EDITION_FIELDS = (
    "id", "slug", "name", "author", "language",
    "attribution", "attribution_required", "awaiting_scholarly_review",
)


# --------------------------------------------------------------------------
# source tree


def load_edition_texts(tree_root, slug):
    """Read one edition into a 6236-long list of str-or-None, in ordinal order.

    A missing file is `None` == NO_COMMENTARY: the edition has nothing for that
    ayah. Empty or whitespace-only text is ALSO None, deliberately — rendering
    an empty pane is the same false signal to the reader as a network error,
    which is the bug this format exists to delete.
    """
    base = os.path.join(tree_root, slug)
    if not os.path.isdir(base):
        raise BuildError(
            "edition %r is declared in editions.json but has no tree at %s.\n"
            "        Either land the extraction or remove the row. The generator "
            "will not silently ship a catalogue entry with no data." % (slug, base))
    texts = [None] * AYAH_COUNT
    blank = 0
    for n, (surah, ayah) in enumerate(iter_positions()):
        path = os.path.join(base, str(surah), "%d.json" % ayah)
        try:
            with open(path, "rb") as fh:
                rec = json.loads(fh.read().decode("utf-8"))
        except IOError:
            continue
        except ValueError as exc:
            raise BuildError("%s is not valid JSON: %s" % (path, exc))
        if rec.get("surah") != surah or rec.get("ayah") != ayah:
            raise BuildError(
                "%s claims surah %r ayah %r — the path is canonical, the record "
                "must agree" % (path, rec.get("surah"), rec.get("ayah")))
        text = rec.get("text")
        if text is None or not str(text).strip():
            blank += 1
            continue
        texts[n] = str(text)
    return texts, blank


# --------------------------------------------------------------------------
# blocks and chunks


def build_blocks(texts):
    """Dedupe by sha256 of the exact UTF-8 text.

    Block ids are assigned in first-appearance order walking ayahs in canonical
    ordinal order. That is what makes the output deterministic, which is what
    makes the manifest's sha256 mean anything.
    """
    blocks = []
    by_digest = {}
    ayah_index = [NO_COMMENTARY] * AYAH_COUNT
    for n, text in enumerate(texts):
        if text is None:
            continue
        raw = text.encode("utf-8")
        digest = hashlib.sha256(raw).digest()
        block_id = by_digest.get(digest)
        if block_id is None:
            block_id = len(blocks)
            if block_id > MAX_BLOCK_ID:
                raise BuildError(
                    "block_count exceeded %d; 0xFFFF is the NO_COMMENTARY "
                    "sentinel and cannot be a block id. The format needs a u32 "
                    "index before this edition can ship." % (MAX_BLOCK_ID + 1))
            blocks.append(raw)
            by_digest[digest] = block_id
        ayah_index[n] = block_id
    return blocks, ayah_index


def pack_chunks(blocks, target):
    """Greedy pack to `target`, never splitting a block.

    THE LOAD-BEARING INVARIANT: every block lies entirely within exactly one
    chunk, so a read is exactly one bounded inflate. A block larger than the
    target gets a chunk to itself (this happens — Elmalılı has one).
    """
    chunks = []
    start = 0
    size = 0
    for i, raw in enumerate(blocks):
        if size > 0 and size + len(raw) > target:
            chunks.append((start, i))
            start, size = i, 0
        size += len(raw)
        if size >= target:
            chunks.append((start, i + 1))
            start, size = i + 1, 0
    if start < len(blocks):
        chunks.append((start, len(blocks)))
    return chunks


def serialize(blocks, ayah_index, target):
    block_table = [0]
    for raw in blocks:
        block_table.append(block_table[-1] + len(raw))
    uncompressed_total = block_table[-1]

    chunks = pack_chunks(blocks, target)

    # Assert the invariant against the tables rather than against the loop that
    # produced them: a reader is entitled to assume it, so it is checked here.
    for c, (b0, b1) in enumerate(chunks):
        raw_lo = block_table[b0]
        raw_hi = block_table[b1]
        for b in range(b0, b1):
            if not (raw_lo <= block_table[b] and block_table[b + 1] <= raw_hi):
                raise BuildError("block %d escapes chunk %d" % (b, c))
    if chunks and chunks[-1][1] != len(blocks):
        raise BuildError("chunking dropped blocks")

    comp = []
    chunk_table = []
    comp_off = 0
    for b0, b1 in chunks:
        raw = b"".join(blocks[b0:b1])
        co = zlib.compressobj(9, zlib.DEFLATED, -15)
        payload = co.compress(raw) + co.flush()
        chunk_table.append((block_table[b0], comp_off))
        comp.append(payload)
        comp_off += len(payload)
    chunk_table.append((uncompressed_total, comp_off))

    ayah_index_off = HEADER_SIZE
    block_table_off = ayah_index_off + 2 * AYAH_COUNT
    chunk_table_off = block_table_off + 4 * len(block_table)
    chunk_data_off = chunk_table_off + 8 * len(chunk_table)

    out = bytearray()
    out += pack_header(
        FLAG_DEFLATE_RAW, len(blocks), ayah_index_off, block_table_off,
        chunk_table_off, chunk_data_off, len(chunks), uncompressed_total)
    for v in ayah_index:
        out += v.to_bytes(2, "little")
    for v in block_table:
        out += v.to_bytes(4, "little")
    for raw_off, c_off in chunk_table:
        out += raw_off.to_bytes(4, "little")
        out += c_off.to_bytes(4, "little")
    for payload in comp:
        out += payload

    return bytes(out), {
        "blocks": len(blocks),
        "chunks": len(chunks),
        "uncompressed_total": uncompressed_total,
        "index_bytes": chunk_data_off,
    }


# --------------------------------------------------------------------------
# per-edition build


def build_edition(edition, tree_root, out_dir, target, verify):
    for field in REQUIRED_EDITION_FIELDS:
        if field not in edition:
            raise BuildError(
                "editions.json row %r is missing %r"
                % (edition.get("slug", "?"), field))
    slug = edition["slug"]
    if edition["attribution_required"] and not (edition["attribution"] or "").strip():
        raise BuildError(
            "%s sets attribution_required but carries no attribution. The "
            "licence makes the credit a condition of the permission, so this is "
            "a build failure, not a warning." % slug)

    texts, blank = load_edition_texts(tree_root, slug)
    blocks, ayah_index = build_blocks(texts)
    if not blocks:
        raise BuildError("%s produced no blocks" % slug)
    data, stats = serialize(blocks, ayah_index, target)

    path = os.path.join(out_dir, "%s.rtb" % slug)
    with open(path, "wb") as fh:
        fh.write(data)

    with_commentary = sum(1 for t in texts if t is not None)
    # `_`-prefixed keys are editorial notes for humans reading editions.json.
    # They stay out of the shipped manifest, which is a contract two apps parse.
    row = {k: v for k, v in edition.items() if not k.startswith("_")}
    row.update({
        "file": "%s.rtb" % slug,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "blocks": stats["blocks"],
        "chunks": stats["chunks"],
        "ayahs_with_commentary": with_commentary,
        "ayahs_without_commentary": AYAH_COUNT - with_commentary,
    })

    if verify:
        row["max_coverage_run"] = verify_edition(path, row, texts)
    else:
        row["max_coverage_run"] = None

    row["_stats"] = {
        "text_bytes": sum(len(t.encode("utf-8")) for t in texts if t is not None),
        "unique_bytes": stats["uncompressed_total"],
        "index_bytes": stats["index_bytes"],
        "blank_records": blank,
    }
    return row


def verify_edition(path, row, texts):
    """Round-trip every record through the reference reader.

    Every one of the edition's records is read back out of the `.rtb` and
    compared to the source text. Also re-derives the coverage stats the manifest
    publishes, so the numbers in the manifest come out of the artifact rather
    than out of the builder's own bookkeeping.
    """
    import rtb_reader

    bundle = rtb_reader.open_bundle(path, row, verify_sha256=True)
    for n, (surah, ayah) in enumerate(iter_positions()):
        got = bundle.read(surah, ayah)
        want = texts[n]
        if want is None:
            if got is not rtb_reader.NO_COMMENTARY_RESULT:
                raise BuildError(
                    "%s %d:%d has no source record but the bundle returns text"
                    % (row["slug"], surah, ayah))
            continue
        if got is rtb_reader.NO_COMMENTARY_RESULT:
            raise BuildError(
                "%s %d:%d round-tripped to NO_COMMENTARY" % (row["slug"], surah, ayah))
        if got.text != want:
            raise BuildError(
                "%s %d:%d round-trip mismatch" % (row["slug"], surah, ayah))
    counted = bundle.count_without_commentary()
    if counted != row["ayahs_without_commentary"]:
        raise BuildError(
            "%s: manifest says %d ayahs without commentary, the bundle has %d"
            % (row["slug"], row["ayahs_without_commentary"], counted))
    return bundle.max_coverage_run()
