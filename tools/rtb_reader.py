"""Reference reader for `.rtb` v1 — the implementation iOS and Android mirror.

This file is normative. If a platform reader disagrees with this one about any
observable behaviour, this one is right and the platform reader is a bug. It is
deliberately short and dependency-free so that a Swift or Kotlin port is a
line-by-line reading, not an interpretation.

Three states, and no fourth (see §3 of the format spec):

    read(surah, ayah) -> TafsirReading(text, attribution, coverage)
                      -> NO_COMMENTARY_RESULT
                      -> raises BundleUnreadable

There is no network state, because there is no network call.
"""

import hashlib
import struct
import zlib

from rtb_format import (
    AYAH_COUNT,
    AYAH_ORDER_VERSION,
    BundleUnreadable,
    HEADER_SIZE,
    NO_COMMENTARY,
    SURAH_AYAH_COUNTS,
    ordinal,
    position,
    unpack_header,
)


def load_manifest(path, app_ayah_order_version=AYAH_ORDER_VERSION):
    """Parse and assert `manifest.json`. The catalogue comes from here.

    `app_ayah_order_version` is the digest the APP derives from the `quran.json`
    it ships — `EmbeddingManifest.ayahOrderDigest(order)` on iOS,
    `AyahOrder.version` on Android. Passing the app's own value rather than a
    literal is the point: the bundle's index is keyed by ordinal, so if the app's
    row order ever drifts from the generator's, every read silently returns a
    neighbouring ayah's commentary. This turns that into a refusal.
    """
    import json
    with open(path, "rb") as fh:
        manifest = json.loads(fh.read().decode("utf-8"))
    if manifest.get("schema") != 1:
        raise BundleUnreadable("manifest schema %r is not 1" % manifest.get("schema"))
    if manifest.get("ayah_count") != AYAH_COUNT:
        raise BundleUnreadable(
            "manifest ayah_count %r, must be %d"
            % (manifest.get("ayah_count"), AYAH_COUNT))
    if manifest.get("ayah_order_version") != app_ayah_order_version:
        raise BundleUnreadable(
            "manifest ayah_order_version %r != the order this app derives (%r)"
            % (manifest.get("ayah_order_version"), app_ayah_order_version))
    editions = manifest.get("editions") or []
    if not editions:
        raise BundleUnreadable("manifest lists no editions")
    return manifest


def reviewed_editions(manifest):
    """What a picker offers. Everything that has cleared the ADR-013 review."""
    return [e for e in manifest["editions"] if not e.get("awaiting_scholarly_review")]


class Coverage(object):
    """The span of ayahs this block serves, within one surah.

    Derived from `ayah_index`, never stored: the contiguous run of ordinals
    around `n` that point at the same block id, clamped to the surah.

    The claim it licenses is about WHAT THE EDITION GIVES for those ayahs, not
    about how the commentary was authored. Both are true statements for the
    same run, so the display copy must be written to hold under either. Do not
    "fix" this into an authorial claim later.
    """

    __slots__ = ("surah", "start_ayah", "end_ayah")

    def __init__(self, surah, start_ayah, end_ayah):
        self.surah = surah
        self.start_ayah = start_ayah
        self.end_ayah = end_ayah

    @property
    def is_range(self):
        return self.end_ayah > self.start_ayah

    @property
    def length(self):
        return self.end_ayah - self.start_ayah + 1

    def __repr__(self):
        return "Coverage(%d:%d-%d)" % (self.surah, self.start_ayah, self.end_ayah)

    def __eq__(self, other):
        return (isinstance(other, Coverage)
                and (self.surah, self.start_ayah, self.end_ayah)
                == (other.surah, other.start_ayah, other.end_ayah))


class TafsirReading(object):
    """One value, not two.

    A call site cannot obtain `text` without also holding `attribution`, so a
    new read surface cannot omit the credit by forgetting. §4 of the spec.
    """

    __slots__ = ("text", "attribution", "coverage")

    def __init__(self, text, attribution, coverage):
        self.text = text
        self.attribution = attribution
        self.coverage = coverage


class _NoCommentary(object):
    """The edition has no commentary for this ayah.

    NOT an error, NOT logged as an error, NO retry affordance. The whole point
    of the bundle: the index knows the difference between silence and failure.
    """

    def __repr__(self):
        return "NO_COMMENTARY"

    def __bool__(self):
        return False

    __nonzero__ = __bool__


NO_COMMENTARY_RESULT = _NoCommentary()


class RtbBundle(object):
    def __init__(self, data, edition, verify_sha256=True):
        """`edition` is the manifest row for this bundle.

        The loader fails closed on attribution: if `attribution_required` is
        true and `attribution` is empty or absent, it refuses to open the
        bundle at all. Not a warning — a refusal.
        """
        self._data = data
        self.edition = edition

        if edition.get("attribution_required"):
            if not (edition.get("attribution") or "").strip():
                raise BundleUnreadable(
                    "%s requires attribution and the manifest carries none"
                    % edition.get("slug"))
        self.attribution = (edition.get("attribution") or "").strip() or None

        if verify_sha256:
            declared = edition.get("sha256")
            if not declared:
                raise BundleUnreadable(
                    "manifest row for %s has no sha256" % edition.get("slug"))
            actual = hashlib.sha256(data).hexdigest()
            if actual != declared:
                raise BundleUnreadable(
                    "sha256 mismatch for %s: manifest %s, bytes %s"
                    % (edition.get("slug"), declared, actual))

        h = unpack_header(data)
        self.__dict__.update(h)
        self._header = h

        if len(data) < self.chunk_data_off:
            raise BundleUnreadable("truncated bundle")

        self._ayah_index = struct.unpack_from(
            "<%dH" % AYAH_COUNT, data, self.ayah_index_off)
        self._block_table = struct.unpack_from(
            "<%dI" % (self.block_count + 1), data, self.block_table_off)
        self._chunk_table = struct.unpack_from(
            "<%dI" % (2 * (self.chunk_count + 1)), data, self.chunk_table_off)
        if self._block_table[-1] != self.uncompressed_total:
            raise BundleUnreadable("block_table sentinel != uncompressed_total")
        self._cache = {}  # chunk id -> inflated bytes (one entry is enough)

    # -- the three-state read ------------------------------------------------

    def read(self, surah, ayah):
        n = ordinal(surah, ayah)
        block_id = self._ayah_index[n]
        if block_id == NO_COMMENTARY:
            return NO_COMMENTARY_RESULT
        if block_id >= self.block_count:
            raise BundleUnreadable(
                "ayah_index[%d] = %d, out of range" % (n, block_id))
        raw = self._block_bytes(block_id)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BundleUnreadable("block %d is not valid UTF-8: %s" % (block_id, exc))
        return TafsirReading(text, self.attribution, self._coverage(n, block_id))

    # -- derived coverage ---------------------------------------------------

    def _coverage(self, n, block_id):
        surah, ayah = position(n)
        first = n - (ayah - 1)
        last = first + SURAH_AYAH_COUNTS[surah - 1] - 1
        start = n
        while start > first and self._ayah_index[start - 1] == block_id:
            start -= 1
        end = n
        while end < last and self._ayah_index[end + 1] == block_id:
            end += 1
        return Coverage(surah, start - first + 1, end - first + 1)

    # -- one bounded inflate per read ---------------------------------------

    def _block_bytes(self, block_id):
        raw_start = self._block_table[block_id]
        raw_end = self._block_table[block_id + 1]
        c = self._chunk_of(raw_start)
        chunk_raw_start = self._chunk_table[2 * c]
        chunk_raw_end = self._chunk_table[2 * (c + 1)]
        if raw_end > chunk_raw_end:
            # The load-bearing invariant. If this fires, the generator is broken.
            raise BundleUnreadable(
                "block %d spans chunks %d.. — invariant violated" % (block_id, c))
        chunk = self._chunk(c)
        return chunk[raw_start - chunk_raw_start:raw_end - chunk_raw_start]

    def _chunk_of(self, raw_off):
        lo, hi = 0, self.chunk_count - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._chunk_table[2 * mid] <= raw_off:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def _chunk(self, c):
        hit = self._cache.get(c)
        if hit is not None:
            return hit
        comp_start = self.chunk_data_off + self._chunk_table[2 * c + 1]
        comp_end = self.chunk_data_off + self._chunk_table[2 * (c + 1) + 1]
        expected = self._chunk_table[2 * (c + 1)] - self._chunk_table[2 * c]
        try:
            out = zlib.decompress(self._data[comp_start:comp_end], -15, expected)
        except zlib.error as exc:
            raise BundleUnreadable("inflate failed on chunk %d: %s" % (c, exc))
        if len(out) != expected:
            raise BundleUnreadable(
                "chunk %d inflated to %d bytes, expected %d"
                % (c, len(out), expected))
        self._cache = {c: out}
        return out

    # -- the manifest assertion that keeps missing-records honest -----------

    def count_without_commentary(self):
        return sum(1 for v in self._ayah_index if v == NO_COMMENTARY)

    def max_coverage_run(self):
        longest = 0
        for s in range(1, 115):
            base = ordinal(s, 1)
            n = base
            end = base + SURAH_AYAH_COUNTS[s - 1]
            while n < end:
                b = self._ayah_index[n]
                m = n + 1
                if b != NO_COMMENTARY:
                    while m < end and self._ayah_index[m] == b:
                        m += 1
                    longest = max(longest, m - n)
                n = m
        return longest


def open_bundle(path, edition, verify_sha256=True):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < HEADER_SIZE:
        raise BundleUnreadable("file too small: %s" % path)
    return RtbBundle(data, edition, verify_sha256=verify_sha256)
