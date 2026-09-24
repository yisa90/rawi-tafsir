#!/usr/bin/env python3
"""Build the `.rtb` tafsir bundles and the manifest both apps consume.

    python3 tools/build-bundles.py                       # everything in editions.json
    python3 tools/build-bundles.py --edition de-mourad    # dev subset, no manifest
    python3 tools/build-bundles.py --no-verify            # skip the round-trip check

One generator, two consumers, never a per-platform builder. The canonical format
spec is `rawi-brain/product/tafsir-bundle-format.md`; this is its only
implementation.

Inputs
    editions.json                        the catalogue (the only edition list)
    tafsir/<slug>/<surah>/<ayah>.json    the reviewable, diffable source of truth

Outputs
    dist/<slug>.rtb
    dist/manifest.json

Everything the manifest reports is DERIVED from the data. No count, coverage
figure or size is written by hand, because the edition set changes and a
hand-written count is a lie waiting for a release.
"""

import argparse
import json
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rtb_format import (  # noqa: E402
    AYAH_COUNT,
    DEFAULT_CHUNK_BYTES,
    ayah_order_digest,
)
from rtb_writer import REPO, BuildError, build_edition  # noqa: E402


# --------------------------------------------------------------------------
# driver


def load_catalogue(path):
    with open(path, "rb") as fh:
        cat = json.loads(fh.read().decode("utf-8"))
    if cat.get("schema") != 1:
        raise BuildError("editions.json schema %r is not 1" % cat.get("schema"))
    editions = cat.get("editions") or []
    if not editions:
        raise BuildError("editions.json lists no editions")
    slugs = [e.get("slug") for e in editions]
    if len(set(slugs)) != len(slugs):
        raise BuildError("duplicate slug in editions.json")
    ids = [e.get("id") for e in editions]
    if len(set(ids)) != len(ids):
        raise BuildError("duplicate id in editions.json")
    return cat, editions


def source_commit():
    try:
        import subprocess
        sha = subprocess.check_output(
            ["git", "-C", REPO, "rev-parse", "HEAD"]).decode().strip()
        dirty = subprocess.check_output(
            ["git", "-C", REPO, "status", "--porcelain", "--", "tafsir", "editions.json"]
        ).decode().strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", default=os.path.join(REPO, "tafsir"))
    ap.add_argument("--catalogue", default=os.path.join(REPO, "editions.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "dist"))
    ap.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES)
    ap.add_argument("--edition", action="append", default=None,
                    help="build a subset; skips the manifest on purpose")
    ap.add_argument("--no-verify", dest="verify", action="store_false", default=True)
    ap.add_argument("--bundle-version", default=None)
    args = ap.parse_args(argv)

    cat, editions = load_catalogue(args.catalogue)

    declared = {e["slug"] for e in editions}
    on_disk = {d for d in os.listdir(args.tree)
               if os.path.isdir(os.path.join(args.tree, d))}
    orphans = sorted(on_disk - declared)

    subset = args.edition
    if subset:
        unknown = [s for s in subset if s not in declared]
        if unknown:
            raise BuildError("--edition %s is not in editions.json" % ", ".join(unknown))
        editions = [e for e in editions if e["slug"] in subset]

    os.makedirs(args.out, exist_ok=True)
    rows = []
    for edition in editions:
        row = build_edition(edition, args.tree, args.out, args.chunk_bytes, args.verify)
        rows.append(row)
        st = row.pop("_stats")
        print("  %-28s %7.3f MB  %5d blocks (%4.2fx)  %4d chunks  "
              "%4d without  run<=%s"
              % (row["slug"], row["bytes"] / 1e6, row["blocks"],
                 (st["text_bytes"] / st["unique_bytes"]) if st["unique_bytes"] else 0,
                 row["chunks"], row["ayahs_without_commentary"],
                 row["max_coverage_run"]))

    total = sum(r["bytes"] for r in rows)
    print("  %-28s %7.3f MB  %5d blocks              %4d chunks"
          % ("TOTAL", total / 1e6, sum(r["blocks"] for r in rows),
             sum(r["chunks"] for r in rows)))

    if orphans:
        print("\n  note: %d tree(s) on disk are not in editions.json and are NOT "
              "bundled:\n        %s" % (len(orphans), ", ".join(orphans)))

    if subset:
        print("\n  subset build — manifest.json NOT written (it must always "
              "describe the whole catalogue)")
        return 0

    manifest = {
        "schema": 1,
        "bundle_version": args.bundle_version or cat.get("bundle_version"),
        "source_commit": source_commit(),
        "ayah_count": AYAH_COUNT,
        "ayah_order_version": ayah_order_digest(),
        "chunk_target_bytes": args.chunk_bytes,
        "compression": "deflate-raw-9",
        "generator": "tools/build-bundles.py (zlib %s)" % zlib.ZLIB_VERSION,
        "editions": rows,
    }
    manifest_path = os.path.join(args.out, "manifest.json")
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print("\n  wrote %s (%d editions)" % (manifest_path, len(rows)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as exc:
        sys.stderr.write("\nbuild failed: %s\n" % exc)
        sys.exit(1)
