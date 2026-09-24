"""`.rtb` v1 — the tafsir bundle container.

Normative reference for the format specified in
`rawi-brain/product/tafsir-bundle-format.md`. This module holds only what the
writer and the reader must agree on: the header, the canonical ayah ordering,
and the sentinel. The iOS and Android readers mirror `rtb_reader.py`.

Stdlib only, on purpose: this runs in CI and on a laptop with no venv.
"""

import hashlib
import struct

MAGIC = b"RTB1"
FORMAT_VERSION = 1

# flags bit 0 — compression. 1 = raw Deflate (RFC 1951, no zlib/gzip wrapper,
# window -15). Every other bit is reserved and MUST be 0; a reader that sees an
# unknown bit fails closed.
FLAG_DEFLATE_RAW = 1 << 0
FLAGS_KNOWN = FLAG_DEFLATE_RAW

AYAH_COUNT = 6236
NO_COMMENTARY = 0xFFFF
MAX_BLOCK_ID = 0xFFFE  # so NO_COMMENTARY stays a safe sentinel
DEFAULT_CHUNK_BYTES = 128 * 1024

HEADER_SIZE = 40
HEADER_STRUCT = struct.Struct("<4sHH" + "I" * 8)
assert HEADER_STRUCT.size == HEADER_SIZE

# The canonical mushaf ayah counts, surah 1..114. This is the SAME ordering as
# `ayah_embeddings.bin` / `position_index.bin`; the bundle does not get its own.
#
# Neither app has a table like this and neither should grow one: both derive the
# order from the `quran.json` they already ship and prove it with a digest. This
# table exists only because rawi-tafsir does not ship `quran.json`, and it is not
# trusted on faith — `AYAH_ORDER_VERSION` below pins it to the digest the two
# apps and rawi-ml already assert, so a typo here fails at import, not in a
# reader handing back the wrong ayah's commentary.
SURAH_AYAH_COUNTS = (
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128,
    111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73,
    54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60,
    49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52,
    44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19,
    26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3,
    6, 3, 5, 4, 5, 6,
)
assert len(SURAH_AYAH_COUNTS) == 114
assert sum(SURAH_AYAH_COUNTS) == AYAH_COUNT

# ordinal of (surah, 1) for each surah, so lookups are O(1) both ways.
_SURAH_START = []
_acc = 0
for _c in SURAH_AYAH_COUNTS:
    _SURAH_START.append(_acc)
    _acc += _c
SURAH_START = tuple(_SURAH_START)


def ordinal(surah, ayah):
    """(surah, ayah) -> global ordinal 0..6235 in canonical mushaf order."""
    if not 1 <= surah <= 114:
        raise ValueError("surah out of range: %r" % (surah,))
    if not 1 <= ayah <= SURAH_AYAH_COUNTS[surah - 1]:
        raise ValueError("ayah out of range for surah %d: %r" % (surah, ayah))
    return SURAH_START[surah - 1] + ayah - 1


def position(n):
    """global ordinal -> (surah, ayah). Inverse of `ordinal`."""
    if not 0 <= n < AYAH_COUNT:
        raise ValueError("ordinal out of range: %r" % (n,))
    lo, hi = 0, 113
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if SURAH_START[mid] <= n:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1, n - SURAH_START[lo] + 1


def iter_positions():
    """All 6236 (surah, ayah) pairs in canonical ordinal order."""
    for s in range(1, 115):
        for a in range(1, SURAH_AYAH_COUNTS[s - 1] + 1):
            yield s, a


def ayah_order_digest():
    """The digest of the canonical row ordering.

    **This is not a new contract.** It is byte-identical to
    `rawi-ml/emit_manifest.ayah_order_hash`, iOS
    `EmbeddingManifest.ayahOrderDigest` and Android `AyahOrder.version`:
    `sha256("s:a,s:a,...")`, first 16 hex characters. The tafsir bundle is keyed
    to the same ordering `ayah_embeddings.bin` and `position_index.bin` are, so
    it asserts against the same value instead of introducing a second digest for
    the same fact.
    """
    payload = ",".join("%d:%d" % (s, a) for s, a in iter_positions())
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]


DIGEST_LENGTH = 16

# The shipping corpus's digest, as pinned by rawi-ml, iOS and Android. A reader
# refuses a bundle whose manifest disagrees with the order the app itself derives
# from quran.json.
AYAH_ORDER_VERSION = "4498d920be9450ff"

assert ayah_order_digest() == AYAH_ORDER_VERSION, (
    "SURAH_AYAH_COUNTS no longer reproduces the shipping ayah order "
    "(%s != %s). Fix the table, do not bump the constant."
    % (ayah_order_digest(), AYAH_ORDER_VERSION))


def pack_header(
    flags,
    block_count,
    ayah_index_off,
    block_table_off,
    chunk_table_off,
    chunk_data_off,
    chunk_count,
    uncompressed_total,
):
    return HEADER_STRUCT.pack(
        MAGIC,
        FORMAT_VERSION,
        flags,
        AYAH_COUNT,
        block_count,
        ayah_index_off,
        block_table_off,
        chunk_table_off,
        chunk_data_off,
        chunk_count,
        uncompressed_total,
    )


class BundleUnreadable(Exception):
    """Header/version/count/inflate assertion failed. A shipped build should
    never raise this: it means the artifact is corrupt."""


def unpack_header(buf):
    if len(buf) < HEADER_SIZE:
        raise BundleUnreadable("short header: %d bytes" % len(buf))
    (magic, version, flags, ayah_count, block_count, ayah_index_off,
     block_table_off, chunk_table_off, chunk_data_off, chunk_count,
     uncompressed_total) = HEADER_STRUCT.unpack_from(buf, 0)
    if magic != MAGIC:
        raise BundleUnreadable("bad magic: %r" % (magic,))
    if version != FORMAT_VERSION:
        raise BundleUnreadable("unsupported format_version: %d" % version)
    if flags & ~FLAGS_KNOWN:
        raise BundleUnreadable("unknown flag bits set: 0x%04x" % flags)
    if not flags & FLAG_DEFLATE_RAW:
        raise BundleUnreadable("compression bit not set: 0x%04x" % flags)
    if ayah_count != AYAH_COUNT:
        raise BundleUnreadable(
            "ayah_count is %d, must be %d" % (ayah_count, AYAH_COUNT))
    if block_count > MAX_BLOCK_ID + 1:
        raise BundleUnreadable("block_count %d exceeds sentinel space" % block_count)
    return {
        "flags": flags,
        "ayah_count": ayah_count,
        "block_count": block_count,
        "ayah_index_off": ayah_index_off,
        "block_table_off": block_table_off,
        "chunk_table_off": chunk_table_off,
        "chunk_data_off": chunk_data_off,
        "chunk_count": chunk_count,
        "uncompressed_total": uncompressed_total,
    }
