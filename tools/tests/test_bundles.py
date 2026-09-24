#!/usr/bin/env python3
"""Tests for the `.rtb` generator and the reference reader.

    python3 tools/tests/test_bundles.py            # fixture only, ~2s
    RTB_REAL_TREE=1 python3 tools/tests/test_bundles.py   # + all real editions, ~1min

Stdlib unittest, no dependencies, so it runs anywhere the generator does.

Each of the generator obligations in the format spec §6 has a test here, named
after it. The real-tree pass is opt-in because it takes a minute; CI runs it.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
FIXTURES = os.path.join(HERE, "fixtures")
sys.path.insert(0, TOOLS)

import rtb_format as F  # noqa: E402
import rtb_reader  # noqa: E402
import rtb_writer  # noqa: E402

REAL = os.environ.get("RTB_REAL_TREE") == "1"


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def load_expectations():
    with open(os.path.join(FIXTURES, "fixture-expectations.json"), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def load_fixture_manifest():
    return rtb_reader.load_manifest(os.path.join(FIXTURES, "fixture-manifest.json"))


class TestCanonicalOrder(unittest.TestCase):
    """The generator reuses the existing 6,236-row ordinal contract."""

    def test_digest_is_the_shipping_one(self):
        # Not a new contract: the same value rawi-ml, iOS and Android assert.
        self.assertEqual(F.ayah_order_digest(), "4498d920be9450ff")
        self.assertEqual(F.ayah_order_digest(), F.AYAH_ORDER_VERSION)

    def test_table_totals(self):
        self.assertEqual(sum(F.SURAH_AYAH_COUNTS), 6236)
        self.assertEqual(len(F.SURAH_AYAH_COUNTS), 114)

    def test_ordinal_roundtrip(self):
        for n, (s, a) in enumerate(F.iter_positions()):
            self.assertEqual(F.ordinal(s, a), n)
            self.assertEqual(F.position(n), (s, a))

    def test_ordinal_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            F.ordinal(2, 287)
        with self.assertRaises(ValueError):
            F.ordinal(115, 1)


class TestChunking(unittest.TestCase):
    """The load-bearing invariant, and the oversized-block path."""

    def test_no_block_spans_a_chunk(self):
        blocks = [b"x" * n for n in (10, 100, 1000, 70000, 70000, 5, 300000, 7)]
        table = [0]
        for b in blocks:
            table.append(table[-1] + len(b))
        chunks = rtb_writer.pack_chunks(blocks, F.DEFAULT_CHUNK_BYTES)
        self.assertEqual(chunks[0][0], 0)
        self.assertEqual(chunks[-1][1], len(blocks))
        for b0, b1 in chunks:
            self.assertLess(b0, b1, "empty chunk")
        # contiguous, ordered, no gaps
        for (a0, a1), (b0, _) in zip(chunks, chunks[1:]):
            self.assertEqual(a1, b0)

    def test_oversized_block_gets_its_own_chunk(self):
        blocks = [b"a" * 10, b"b" * 300000, b"c" * 10]
        chunks = rtb_writer.pack_chunks(blocks, F.DEFAULT_CHUNK_BYTES)
        self.assertIn((1, 2), chunks, "the oversized block must be alone: %r" % (chunks,))

    def test_block_count_ceiling_is_enforced(self):
        # 0xFFFF must stay a sentinel, so 0xFFFE is the last usable block id.
        texts = ["block %d" % i for i in range(F.AYAH_COUNT)]
        blocks, index = rtb_writer.build_blocks(texts)
        self.assertLessEqual(len(blocks), F.MAX_BLOCK_ID + 1)
        self.assertTrue(all(v != F.NO_COMMENTARY for v in index))


class TestFixtureIsGolden(unittest.TestCase):
    """The committed fixture is the artifact iOS and Android assert against too.

    If these fail, do not regenerate the fixture to make them pass: the fixture
    is a contract three readers share, and changing it silently re-points the
    other two platforms' tests.
    """

    def setUp(self):
        self.exp = load_expectations()
        self.manifest = load_fixture_manifest()
        self.row = self.manifest["editions"][0]
        self.bundle = rtb_reader.open_bundle(
            os.path.join(FIXTURES, self.exp["file"]), self.row)

    def test_committed_bytes_match_the_expectations(self):
        data = read_bytes(os.path.join(FIXTURES, self.exp["file"]))
        self.assertEqual(len(data), self.exp["bytes"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.exp["sha256"])

    def test_regenerating_the_fixture_is_deterministic(self):
        before = read_bytes(os.path.join(FIXTURES, self.exp["file"]))
        subprocess.check_output(
            [sys.executable, os.path.join(HERE, "make_fixture.py")])
        after = read_bytes(os.path.join(FIXTURES, self.exp["file"]))
        self.assertEqual(before, after, "fixture generation is not deterministic")

    def test_header(self):
        self.assertEqual(self.bundle.ayah_count, self.exp["ayah_count"])
        self.assertEqual(self.bundle.block_count, self.exp["block_count"])
        self.assertEqual(self.bundle.chunk_count, self.exp["chunk_count"])

    def test_probes(self):
        for p in self.exp["probes"]:
            got = self.bundle.read(p["surah"], p["ayah"])
            where = "%d:%d" % (p["surah"], p["ayah"])
            if p["state"] == "noCommentary":
                self.assertIs(got, rtb_reader.NO_COMMENTARY_RESULT, where)
                continue
            self.assertIsNot(got, rtb_reader.NO_COMMENTARY_RESULT, where)
            self.assertEqual(
                hashlib.sha256(got.text.encode("utf-8")).hexdigest(),
                p["text_sha256"], where)
            self.assertEqual(got.attribution, p["attribution"], where)
            self.assertEqual(got.coverage.start_ayah, p["coverage_start_ayah"], where)
            self.assertEqual(got.coverage.end_ayah, p["coverage_end_ayah"], where)
            self.assertEqual(got.coverage.is_range, p["is_range"], where)

    def test_no_commentary_count_matches_the_manifest(self):
        self.assertEqual(
            self.bundle.count_without_commentary(),
            self.row["ayahs_without_commentary"])
        self.assertEqual(
            self.row["ayahs_without_commentary"],
            self.exp["ayahs_without_commentary"])
        self.assertGreater(
            self.exp["ayahs_without_commentary"], 0,
            "the fixture must exercise a NON-ZERO missing-record count — no "
            "shipping edition has one right now")

    def test_coverage_clamps_to_the_surah(self):
        # 2:286 and 3:1 share a block and are adjacent ordinals.
        a = self.bundle.read(2, 286)
        b = self.bundle.read(3, 1)
        self.assertEqual(a.text, b.text)
        self.assertEqual((a.coverage.surah, a.coverage.start_ayah, a.coverage.end_ayah),
                         (2, 286, 286))
        self.assertEqual((b.coverage.surah, b.coverage.start_ayah, b.coverage.end_ayah),
                         (3, 1, 1))

    def test_distant_duplicates_are_not_a_range(self):
        for s, a in ((5, 10), (90, 2)):
            r = self.bundle.read(s, a)
            self.assertFalse(r.coverage.is_range, "%d:%d" % (s, a))

    def test_range_block_reads_the_same_at_every_member(self):
        first = self.bundle.read(2, 1)
        for a in range(1, 21):
            r = self.bundle.read(2, a)
            self.assertEqual(r.text, first.text)
            self.assertEqual(r.coverage.start_ayah, 1)
            self.assertEqual(r.coverage.end_ayah, 20)

    def test_every_record_round_trips(self):
        for n, (s, a) in enumerate(F.iter_positions()):
            got = self.bundle.read(s, a)
            if n in set(self.exp["no_commentary_ordinals"]):
                self.assertIs(got, rtb_reader.NO_COMMENTARY_RESULT)
            else:
                self.assertIsNot(got, rtb_reader.NO_COMMENTARY_RESULT)
                self.assertTrue(got.text)


class TestReaderFailsClosed(unittest.TestCase):
    """States three and four: `bundleUnreadable`, and nothing else."""

    def setUp(self):
        self.path = os.path.join(FIXTURES, "fixture-edition.rtb")
        self.row = load_fixture_manifest()["editions"][0]

    def _refuse(self, **override):
        row = dict(self.row)
        row.update(override)
        with self.assertRaises(F.BundleUnreadable):
            rtb_reader.open_bundle(self.path, row)

    def test_refuses_when_required_attribution_is_missing(self):
        self._refuse(attribution=None)
        self._refuse(attribution="   ")

    def test_refuses_on_sha256_mismatch(self):
        self._refuse(sha256="0" * 64)

    def test_refuses_when_the_manifest_has_no_sha256(self):
        row = dict(self.row)
        del row["sha256"]
        with self.assertRaises(F.BundleUnreadable):
            rtb_reader.open_bundle(self.path, row)

    def test_refusal_cases_in_the_fixture_are_all_covered(self):
        for case in load_expectations()["refusal_cases"]:
            self.assertEqual(case["expect"], "bundleUnreadable")
            self._refuse(**case["manifest_row_override"])

    def test_rejects_bad_magic(self):
        data = bytearray(read_bytes(self.path))
        data[0:4] = b"XXXX"
        with self.assertRaises(F.BundleUnreadable):
            F.unpack_header(bytes(data))

    def test_rejects_unknown_flag_bits(self):
        data = bytearray(read_bytes(self.path))
        data[6:8] = (F.FLAG_DEFLATE_RAW | 0x8000).to_bytes(2, "little")
        with self.assertRaises(F.BundleUnreadable):
            F.unpack_header(bytes(data))

    def test_rejects_wrong_ayah_count(self):
        data = bytearray(read_bytes(self.path))
        data[8:12] = (6235).to_bytes(4, "little")
        with self.assertRaises(F.BundleUnreadable):
            F.unpack_header(bytes(data))

    def test_manifest_refuses_a_foreign_ayah_order(self):
        with self.assertRaises(F.BundleUnreadable):
            rtb_reader.load_manifest(
                os.path.join(FIXTURES, "fixture-manifest.json"),
                app_ayah_order_version="deadbeefdeadbeef")


class TestCatalogue(unittest.TestCase):
    """editions.json is the only edition list, and it fails closed."""

    def setUp(self):
        with open(os.path.join(REPO, "editions.json"), "rb") as fh:
            self.cat = json.loads(fh.read().decode("utf-8"))
        self.editions = self.cat["editions"]

    def test_every_row_has_every_required_field(self):
        for e in self.editions:
            for field in rtb_writer.REQUIRED_EDITION_FIELDS:
                self.assertIn(field, e, e.get("slug"))

    def test_ids_and_slugs_are_unique(self):
        slugs = [e["slug"] for e in self.editions]
        ids = [e["id"] for e in self.editions]
        self.assertEqual(len(set(slugs)), len(slugs))
        self.assertEqual(len(set(ids)), len(ids))

    def test_the_misspelled_slug_is_still_misspelled(self):
        # Load-bearing: the corrected spelling 403s on the CDN and the slug is
        # what a saved preference and both platforms' tests point at.
        self.assertIn("en-tafisr-ibn-kathir", [e["slug"] for e in self.editions])
        self.assertNotIn("en-tafsir-ibn-kathir", [e["slug"] for e in self.editions])

    def test_free_edition_169_is_present_and_reviewed(self):
        free = [e for e in self.editions if e["id"] == 169]
        self.assertEqual(len(free), 1)
        self.assertFalse(free[0]["awaiting_scholarly_review"])

    def test_language_is_a_code_not_a_display_string(self):
        for e in self.editions:
            self.assertRegex(e["language"], r"^[a-z]{2}$", e["slug"])

    def test_attribution_required_implies_attribution(self):
        for e in self.editions:
            if e["attribution_required"]:
                self.assertTrue((e["attribution"] or "").strip(), e["slug"])

    def test_reviewed_edition_count_is_nine(self):
        # The German gate (ADR-013): the bundle may contain a German edition,
        # the pickers do not offer it. Both app suites assert the same nine.
        reviewed = [e for e in self.editions if not e["awaiting_scholarly_review"]]
        self.assertEqual(len(reviewed), 9)

    def test_every_declared_edition_has_a_tree(self):
        for e in self.editions:
            self.assertTrue(
                os.path.isdir(os.path.join(REPO, "tafsir", e["slug"])),
                "%s is declared but has no tree" % e["slug"])


class TestGeneratorFailsClosed(unittest.TestCase):

    def test_missing_tree_is_a_build_failure(self):
        with self.assertRaises(rtb_writer.BuildError):
            rtb_writer.load_edition_texts(os.path.join(REPO, "tafsir"), "de-nonexistent")

    def test_attribution_required_with_none_is_a_build_failure(self):
        tmp = tempfile.mkdtemp()
        try:
            bad = {
                "id": 1, "slug": "en-tafisr-ibn-kathir", "name": "x", "author": "y",
                "language": "en", "attribution": None,
                "attribution_required": True, "awaiting_scholarly_review": False,
            }
            with self.assertRaises(rtb_writer.BuildError):
                rtb_writer.build_edition(
                    bad, os.path.join(REPO, "tafsir"), tmp,
                    F.DEFAULT_CHUNK_BYTES, False)
        finally:
            shutil.rmtree(tmp)

    def test_missing_required_field_is_a_build_failure(self):
        tmp = tempfile.mkdtemp()
        try:
            with self.assertRaises(rtb_writer.BuildError):
                rtb_writer.build_edition(
                    {"slug": "en-tafisr-ibn-kathir"},
                    os.path.join(REPO, "tafsir"), tmp, F.DEFAULT_CHUNK_BYTES, False)
        finally:
            shutil.rmtree(tmp)


@unittest.skipUnless(REAL, "set RTB_REAL_TREE=1 to build the real editions")
class TestRealEditions(unittest.TestCase):
    """The full build: round-trip, determinism, and the manifest's own numbers."""

    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp()
        subprocess.check_output([
            sys.executable, os.path.join(TOOLS, "build-bundles.py"),
            "--out", cls.out])
        cls.manifest = rtb_reader.load_manifest(os.path.join(cls.out, "manifest.json"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out)

    def test_manifest_shape(self):
        self.assertEqual(self.manifest["ayah_count"], 6236)
        self.assertEqual(self.manifest["ayah_order_version"], "4498d920be9450ff")
        self.assertEqual(self.manifest["chunk_target_bytes"], 131072)
        self.assertEqual(self.manifest["compression"], "deflate-raw-9")

    def test_every_edition_opens_and_the_counts_are_derived(self):
        for e in self.manifest["editions"]:
            bundle = rtb_reader.open_bundle(os.path.join(self.out, e["file"]), e)
            self.assertEqual(
                bundle.count_without_commentary(), e["ayahs_without_commentary"],
                e["slug"])
            self.assertEqual(
                e["ayahs_with_commentary"] + e["ayahs_without_commentary"], 6236)
            self.assertLessEqual(e["blocks"], F.MAX_BLOCK_ID + 1)

    def test_determinism(self):
        second = tempfile.mkdtemp()
        try:
            subprocess.check_output([
                sys.executable, os.path.join(TOOLS, "build-bundles.py"),
                "--out", second, "--no-verify"])
            for e in self.manifest["editions"]:
                a = read_bytes(os.path.join(self.out, e["file"]))
                b = read_bytes(os.path.join(second, e["file"]))
                self.assertEqual(hashlib.sha256(a).hexdigest(),
                                 hashlib.sha256(b).hexdigest(), e["slug"])
                self.assertEqual(hashlib.sha256(a).hexdigest(), e["sha256"], e["slug"])
        finally:
            shutil.rmtree(second)

    def test_records_round_trip_against_the_source_json(self):
        for e in self.manifest["editions"]:
            bundle = rtb_reader.open_bundle(os.path.join(self.out, e["file"]), e)
            base = os.path.join(REPO, "tafsir", e["slug"])
            for s, a in F.iter_positions():
                path = os.path.join(base, str(s), "%d.json" % a)
                got = bundle.read(s, a)
                if not os.path.exists(path):
                    self.assertIs(got, rtb_reader.NO_COMMENTARY_RESULT)
                    continue
                with open(path, "rb") as fh:
                    want = json.loads(fh.read().decode("utf-8"))["text"]
                self.assertEqual(got.text, want, "%s %d:%d" % (e["slug"], s, a))


if __name__ == "__main__":
    unittest.main(verbosity=2)
